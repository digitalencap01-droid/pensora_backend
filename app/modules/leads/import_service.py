import csv
import io
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.leads import Lead, LeadActivity, LeadImportJob
from app.modules.leads.repository import LeadRepository

STANDARD_FIELD_ALIASES = {
    "email": ["email", "e-mail", "email_address", "email address", "contact_email"],
    "first_name": ["first_name", "first name", "firstname", "fname", "given name"],
    "last_name": ["last_name", "last name", "lastname", "lname", "surname", "family name"],
    "phone": ["phone", "mobile", "phone_number", "phone number", "cell", "contact_number"],
    "company_name": ["company", "company_name", "company name", "organization", "org"],
    "job_title": ["title", "job_title", "job title", "designation", "role"],
    "status": ["status", "lead_status", "stage"],
    "lead_score": ["score", "lead_score", "points"],
}


class LeadImportService:
    @staticmethod
    def preview_csv(csv_content: str) -> dict:
        f = io.StringIO(csv_content.strip())
        reader = csv.reader(f)

        try:
            headers = next(reader)
        except StopIteration:
            return {
                "headers": [],
                "sample_rows": [],
                "suggested_mappings": {},
                "total_rows": 0,
            }

        headers = [h.strip() for h in headers if h.strip()]
        sample_rows = []
        total_rows = 0

        for i, row in enumerate(reader):
            total_rows += 1
            if i < 5:
                row_dict = {
                    headers[j]: row[j].strip()
                    for j in range(min(len(headers), len(row)))
                }
                sample_rows.append(row_dict)

        # Auto suggest field mappings
        suggested_mappings = {}
        for header in headers:
            normalized_header = header.lower().strip()
            mapped = False
            for target_field, aliases in STANDARD_FIELD_ALIASES.items():
                if normalized_header in aliases:
                    suggested_mappings[header] = target_field
                    mapped = True
                    break
            if not mapped:
                suggested_mappings[header] = f"custom:{header}"

        return {
            "headers": headers,
            "sample_rows": sample_rows,
            "suggested_mappings": suggested_mappings,
            "total_rows": total_rows,
        }

    @staticmethod
    async def process_csv_import(
        session: AsyncSession,
        workspace_id: UUID,
        job_id: UUID,
        csv_content: str,
        field_mappings: dict[str, str],
    ) -> LeadImportJob:
        repo = LeadRepository(session)
        job = await repo.get_import_job(workspace_id, job_id)
        if not job:
            raise ValueError(f"Import job {job_id} not found")

        job.status = "processing"
        job.started_at = datetime.utcnow()

        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)

        processed = 0
        successful = 0
        failed = 0
        duplicates = 0
        error_log = []

        for row_idx, row in enumerate(reader, start=1):
            processed += 1
            try:
                lead_data = {}
                custom_fields = {}

                for csv_header, target_field in field_mappings.items():
                    val = row.get(csv_header, "").strip()
                    if not val:
                        continue

                    if target_field.startswith("custom:"):
                        custom_key = target_field.replace("custom:", "")
                        custom_fields[custom_key] = val
                    elif target_field in STANDARD_FIELD_ALIASES:
                        lead_data[target_field] = val

                email = lead_data.get("email")
                if email:
                    existing = await repo.get_by_email(workspace_id, email)
                    if existing:
                        duplicates += 1
                        continue

                if not email and not lead_data.get("phone") and not lead_data.get("first_name"):
                    failed += 1
                    error_log.append(f"Row {row_idx}: Missing email or name/phone identifier.")
                    continue

                new_lead = Lead(
                    workspace_id=workspace_id,
                    first_name=lead_data.get("first_name"),
                    last_name=lead_data.get("last_name"),
                    email=email,
                    phone=lead_data.get("phone"),
                    company_name=lead_data.get("company_name"),
                    job_title=lead_data.get("job_title"),
                    status=lead_data.get("status", "new"),
                    source="csv_import",
                    custom_fields_json=custom_fields,
                )
                await repo.create(new_lead)

                # Activity record
                activity = LeadActivity(
                    workspace_id=workspace_id,
                    lead_id=new_lead.id,
                    activity_type="imported",
                    title="Lead Imported",
                    description=f"Imported via CSV file {job.filename}",
                )
                session.add(activity)
                successful += 1

            except Exception as e:
                failed += 1
                error_log.append(f"Row {row_idx}: {str(e)}")

        job.processed_rows = processed
        job.successful_rows = successful
        job.failed_rows = failed
        job.duplicate_rows = duplicates
        job.error_log_json = error_log[:100]  # Cap error log at 100 entries
        job.status = "completed" if failed == 0 else "completed_with_errors"
        job.completed_at = datetime.utcnow()

        await session.commit()
        return job
