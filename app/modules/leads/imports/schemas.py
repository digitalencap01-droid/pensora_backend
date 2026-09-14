from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SheetInfo(BaseModel):
    name: str
    rows: int


class FileUploadResponse(BaseModel):
    import_id: UUID
    filename: str
    detected_type: str
    mime_type: str
    file_size_bytes: int
    confidence: float
    sheets: list[SheetInfo]
    selected_sheet: str | None = None


class ColumnMappingSuggestion(BaseModel):
    suggested_field: str
    confidence: float


class PreviewMappingResponse(BaseModel):
    import_id: UUID
    filename: str
    detected_type: str
    selected_sheet: str | None = None
    headers: list[str]
    sample_rows: list[dict[str, str]]
    auto_mappings: dict[str, ColumnMappingSuggestion]
    total_rows: int


class ConfirmMappingRequest(BaseModel):
    selected_sheet: str | None = None
    field_mappings: dict[str, str]  # Header -> Canonical Field Name


class ValidationSummaryResponse(BaseModel):
    import_id: UUID
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    sample_errors: list[dict]


class StartImportRequest(BaseModel):
    field_mappings: dict[str, str]
    duplicate_strategy: str = "add_and_update"  # "add_and_update", "add_new_only", "update_only"
    import_mode: str = "all"  # "all", "valid_only"


class ImportSessionStatusResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    filename: str
    status: str  # "uploaded", "mapped", "processing", "completed", "completed_with_errors", "failed"
    detected_type: str
    total_rows: int
    processed_rows: int
    successful_rows: int
    updated_rows: int
    duplicate_rows: int
    failed_rows: int
    field_mappings: dict
    error_log: list
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
