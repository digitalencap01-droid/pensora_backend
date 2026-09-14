from uuid import UUID, uuid4
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.modules.leads.import_detector import FileFormatDetector
from app.modules.leads.import_mapping import MappingService
from app.modules.leads.import_parsers import ParserFactory
from app.modules.leads.import_schemas import (
    FileUploadResponse,
    ImportSessionStatusResponse,
    PreviewMappingResponse,
    StartImportRequest,
)
from app.modules.leads.import_service import UPLOAD_CACHE, UniversalLeadImportService
from app.modules.leads.schemas import (
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from app.modules.leads.supabase_repository import SupabaseLeadRepository

router = APIRouter(prefix="/api/v1/leads", tags=["Leads & Audience CRM"])

DEFAULT_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000000")


@router.get("", response_model=LeadListResponse)
async def list_leads(
    search: str | None = None,
    status: str | None = None,
    source: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=250),
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    repo = SupabaseLeadRepository()
    items, total = await repo.list_leads(
        workspace_id=workspace_id,
        search=search,
        status=status,
        source=source,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return LeadListResponse(
        items=[LeadResponse.model_validate(item.model_dump()) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadCreate,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    repo = SupabaseLeadRepository()
    payload = data.model_dump()
    payload["workspace_id"] = str(workspace_id)
    lead = await repo.create(payload)
    return LeadResponse.model_validate(lead.model_dump())


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    repo = SupabaseLeadRepository()
    lead = await repo.get_by_id(workspace_id, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead.model_dump())


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    repo = SupabaseLeadRepository()
    payload = data.model_dump(exclude_unset=True)
    lead = await repo.update(lead_id, payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead.model_dump())


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    repo = SupabaseLeadRepository()
    success = await repo.delete(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")


# ------------------------------------------------------------------
# Universal Lead Import Engine Endpoints (CSV, XLSX, TSV, JSON)
# ------------------------------------------------------------------


@router.post("/import/upload", response_model=FileUploadResponse)
async def upload_import_file(
    file: UploadFile = File(...),
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    job, result = await UniversalLeadImportService.create_import_session_supabase(
        workspace_id=workspace_id,
        filename=file.filename or "leads_import",
        file_bytes=file_bytes,
    )

    detection = result["detection"]
    parsed = result["parsed"]

    return FileUploadResponse(
        import_id=job["id"],
        filename=job["filename"],
        detected_type=detection["detected_type"],
        mime_type=detection["mime_type"],
        file_size_bytes=len(file_bytes),
        confidence=detection["confidence"],
        sheets=parsed["sheets"],
        selected_sheet=parsed["selected_sheet"],
    )


@router.get("/import/{import_id}/preview", response_model=PreviewMappingResponse)
async def preview_import_mapping(
    import_id: UUID,
    sheet_name: str | None = None,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    file_bytes = UPLOAD_CACHE.get(import_id)
    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="File bytes expired or missing from cache. Please re-upload.",
        )

    # Simple mock job struct for preview parser
    job_struct = {"id": import_id, "filename": "leads_import"}
    preview = UniversalLeadImportService.get_preview(
        job=job_struct, file_bytes=file_bytes, sheet_name=sheet_name
    )
    return PreviewMappingResponse(**preview)


@router.post("/import/{import_id}/start", response_model=ImportSessionStatusResponse)
async def start_import(
    import_id: UUID,
    payload: StartImportRequest,
    selected_sheet: str | None = None,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    file_bytes = UPLOAD_CACHE.get(import_id)
    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="File bytes expired or missing from cache. Please re-upload.",
        )

    completed_job = await UniversalLeadImportService.execute_import_supabase(
        workspace_id=workspace_id,
        job_id=import_id,
        file_bytes=file_bytes,
        field_mappings=payload.field_mappings,
        duplicate_strategy=payload.duplicate_strategy,
        selected_sheet=selected_sheet,
    )

    return ImportSessionStatusResponse(
        id=completed_job["id"],
        workspace_id=completed_job["workspace_id"],
        filename=completed_job["filename"],
        status=completed_job["status"],
        detected_type="auto",
        total_rows=completed_job["total_rows"],
        processed_rows=completed_job["processed_rows"],
        successful_rows=completed_job["successful_rows"],
        updated_rows=completed_job.get("duplicate_rows", 0),
        duplicate_rows=completed_job.get("duplicate_rows", 0),
        failed_rows=completed_job.get("failed_rows", 0),
        field_mappings=completed_job.get("field_mappings_json", {}),
        error_log=completed_job.get("error_log_json", []),
        started_at=completed_job.get("started_at"),
        completed_at=completed_job.get("completed_at"),
        created_at=completed_job.get("created_at"),
    )


@router.post("/import/direct", response_model=ImportSessionStatusResponse)
async def direct_auto_import(
    file: UploadFile | None = File(None),
    csv_text: str | None = Form(None),
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
):
    file_bytes = b""
    filename = "leads_import.csv"

    if file and file.filename:
        file_bytes = await file.read()
        filename = file.filename
    elif csv_text and csv_text.strip():
        file_bytes = csv_text.strip().encode("utf-8")
        filename = "pasted_leads.csv"
    else:
        raise HTTPException(status_code=400, detail="Either file or csv_text must be provided")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Import payload is empty")

    job_id = uuid4()
    detection = FileFormatDetector.detect(filename, file_bytes)
    parser = ParserFactory.get(detection["detected_type"])
    parsed_data = parser.parse(file_bytes)

    raw_auto_mappings = MappingService.auto_map_headers(parsed_data["headers"])
    field_mappings = {
        header: info["suggested_field"]
        for header, info in raw_auto_mappings.items()
    }

    completed_job = await UniversalLeadImportService.execute_import_supabase(
        workspace_id=workspace_id,
        job_id=job_id,
        file_bytes=file_bytes,
        field_mappings=field_mappings,
        duplicate_strategy="add_and_update",
        selected_sheet=parsed_data.get("selected_sheet"),
    )

    return ImportSessionStatusResponse(
        id=completed_job["id"],
        workspace_id=completed_job["workspace_id"],
        filename=filename,
        status=completed_job["status"],
        detected_type=detection["detected_type"],
        total_rows=completed_job["total_rows"],
        processed_rows=completed_job["processed_rows"],
        successful_rows=completed_job["successful_rows"],
        updated_rows=completed_job.get("duplicate_rows", 0),
        duplicate_rows=completed_job.get("duplicate_rows", 0),
        failed_rows=completed_job.get("failed_rows", 0),
        field_mappings=completed_job.get("field_mappings_json", {}),
        error_log=completed_job.get("error_log_json", []),
        started_at=completed_job.get("started_at"),
        completed_at=completed_job.get("completed_at"),
        created_at=completed_job.get("created_at"),
    )
