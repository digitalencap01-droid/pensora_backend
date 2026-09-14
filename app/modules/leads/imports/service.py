from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.leads import Lead, LeadActivity, LeadImportJob
from app.modules.leads.imports.deduplication_service import DeduplicationService
from app.modules.leads.imports.detector import FileFormatDetector
from app.modules.leads.imports.mapping_service import MappingService
from app.modules.leads.imports.normalization_service import NormalizationService
from app.modules.leads.imports.parser_factory import ParserFactory
from app.modules.leads.imports.validation_service import ValidationService
from app.modules.leads.repository import LeadRepository
from app.modules.leads.supabase_repository import SupabaseLeadRepository

# In-memory storage for transient upload payloads during import session
UPLOAD_CACHE: dict[UUID, bytes] = {}


class UniversalLeadImportService:
    @staticmethod
    async def create_import_session_supabase(
        workspace_id: UUID,
        filename: str,
        file_bytes: bytes,
    ) -> tuple[dict, dict]:
        detection = FileFormatDetector.detect(filename, file_bytes)
        parser = ParserFactory.get(detection["detected_type"])
        parsed_data = parser.parse(file_bytes)

        job_id = uuid4()
        job = {
            "id": job_id,
            "workspace_id": workspace_id,
            "filename": filename,
            "file_size_bytes": len(file_bytes),
            "total_rows": len(parsed_data["rows"]),
            "status": "uploaded",
            "field_mappings_json": {},
            "error_log_json": [],
        }

        # Cache file bytes for subsequent mapping/validation/start steps
        UPLOAD_CACHE[job_id] = file_bytes

        return job, {
            "detection": detection,
            "parsed": parsed_data,
        }

    @staticmethod
    def get_preview(
        job: dict | LeadImportJob,
        file_bytes: bytes,
        sheet_name: str | None = None,
    ) -> dict:
        filename = job.filename if hasattr(job, "filename") else job.get("filename", "leads_import")
        job_id = job.id if hasattr(job, "id") else job.get("id")

        detection = FileFormatDetector.detect(filename, file_bytes)
        parser = ParserFactory.get(detection["detected_type"])
        parsed_data = parser.parse(file_bytes, sheet_name=sheet_name)

        auto_mappings = MappingService.auto_map_headers(parsed_data["headers"])

        return {
            "import_id": job_id,
            "filename": filename,
            "detected_type": detection["detected_type"],
            "selected_sheet": parsed_data["selected_sheet"],
            "headers": parsed_data["headers"],
            "sample_rows": parsed_data["rows"][:5],
            "auto_mappings": auto_mappings,
            "total_rows": len(parsed_data["rows"]),
        }

    @staticmethod
    async def execute_import_supabase(
        workspace_id: UUID,
        job_id: UUID,
        file_bytes: bytes,
        field_mappings: dict[str, str],
        duplicate_strategy: str = "add_and_update",
        selected_sheet: str | None = None,
    ) -> dict:
        sb_repo = SupabaseLeadRepository()
        detection = FileFormatDetector.detect("leads_import", file_bytes)
        parser = ParserFactory.get(detection["detected_type"])
        parsed_data = parser.parse(file_bytes, sheet_name=selected_sheet)

        processed = 0
        successful = 0
        duplicates = 0
        failed = 0
        error_log = []

        for row_idx, row in enumerate(parsed_data["rows"], start=1):
            processed += 1
            try:
                mapped_data = {}
                custom_fields = {}

                # 1. First process explicit field mappings
                for header, target_field in field_mappings.items():
                    raw_val = row.get(header, "")
                    normalized = NormalizationService.normalize_value(raw_val)
                    if not normalized:
                        continue

                    if target_field.startswith("custom:"):
                        custom_key = target_field.replace("custom:", "").strip()
                        custom_fields[custom_key] = normalized
                    elif target_field == "email":
                        mapped_data["email"] = NormalizationService.normalize_email(normalized)
                    elif target_field == "phone":
                        mapped_data["phone"] = NormalizationService.normalize_phone(normalized)
                    elif target_field in ["first_name", "last_name", "full_name"]:
                        mapped_data[target_field] = NormalizationService.normalize_name(normalized)
                    else:
                        mapped_data[target_field] = normalized

                # 2. Dynamic inspection for unmapped fields in row
                for raw_header, raw_val in row.items():
                    if not raw_val or not str(raw_val).strip():
                        continue
                    clean_val = str(raw_val).strip()
                    norm_header = str(raw_header).lower().strip().replace("-", "_").replace(" ", "_")

                    if norm_header in ["email", "e_mail", "email_address", "contact_email"] and "email" not in mapped_data:
                        mapped_data["email"] = NormalizationService.normalize_email(clean_val)
                    elif norm_header in ["phone", "mobile", "phone_number", "contact_number", "cell"] and "phone" not in mapped_data:
                        mapped_data["phone"] = NormalizationService.normalize_phone(clean_val)
                    elif norm_header in ["name", "full_name", "lead_name", "contact_name"] and "full_name" not in mapped_data:
                        mapped_data["full_name"] = NormalizationService.normalize_name(clean_val)
                    elif norm_header in ["first_name", "fname", "firstname"] and "first_name" not in mapped_data:
                        mapped_data["first_name"] = NormalizationService.normalize_name(clean_val)
                    elif norm_header in ["last_name", "lname", "lastname"] and "last_name" not in mapped_data:
                        mapped_data["last_name"] = NormalizationService.normalize_name(clean_val)
                    elif norm_header in ["company", "company_name", "organization", "org", "business"] and "company_name" not in mapped_data:
                        mapped_data["company_name"] = clean_val
                    elif norm_header in ["title", "job_title", "role", "designation", "position"] and "job_title" not in mapped_data:
                        mapped_data["job_title"] = clean_val
                    elif norm_header in ["status", "lead_status", "stage", "lifecycle_stage"] and "status" not in mapped_data:
                        mapped_data["status"] = clean_val
                    elif norm_header in ["source", "lead_source", "channel"] and "source" not in mapped_data:
                        mapped_data["source"] = clean_val
                    elif norm_header in ["score", "lead_score", "points"] and "lead_score" not in mapped_data:
                        try:
                            mapped_data["lead_score"] = int(float(clean_val))
                        except Exception:
                            mapped_data["lead_score"] = 50
                    elif norm_header in ["tags", "tag", "labels"] and "tags" not in mapped_data:
                        mapped_data["tags"] = [t.strip() for t in clean_val.replace(";", ",").split(",") if t.strip()]
                    elif raw_header not in field_mappings:
                        custom_fields[raw_header] = clean_val

                is_valid, errors = ValidationService.validate_row(mapped_data)
                if not is_valid and not mapped_data.get("company_name"):
                    failed += 1
                    error_log.append({"row": row_idx, "errors": errors})
                    continue

                new_lead = {
                    "id": str(uuid4()),
                    "workspace_id": str(workspace_id),
                    "first_name": mapped_data.get("first_name"),
                    "last_name": mapped_data.get("last_name"),
                    "full_name": mapped_data.get("full_name"),
                    "email": mapped_data.get("email"),
                    "phone": mapped_data.get("phone"),
                    "company_name": mapped_data.get("company_name"),
                    "job_title": mapped_data.get("job_title"),
                    "status": mapped_data.get("status", "new"),
                    "source": mapped_data.get("source", "import"),
                    "lead_score": mapped_data.get("lead_score", 0),
                    "tags": mapped_data.get("tags", []),
                    "custom_fields_json": custom_fields,
                }
                await sb_repo.create(new_lead)
                successful += 1

            except Exception as e:
                failed += 1
                error_log.append({"row": row_idx, "errors": [str(e)]})

        completed_job = {
            "id": job_id,
            "workspace_id": workspace_id,
            "filename": "leads_import",
            "status": "completed" if failed == 0 else "completed_with_errors",
            "total_rows": len(parsed_data["rows"]),
            "processed_rows": processed,
            "successful_rows": successful,
            "duplicate_rows": duplicates,
            "failed_rows": failed,
            "field_mappings_json": field_mappings,
            "error_log_json": error_log[:100],
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }

        return completed_job
