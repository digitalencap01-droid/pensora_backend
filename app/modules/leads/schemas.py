from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LeadBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    status: str = "new"
    source: str = "manual"
    lead_score: int = 0
    tags: list[str] = Field(default_factory=list)
    custom_fields_json: dict = Field(default_factory=dict)
    is_subscribed_email: bool = True
    is_subscribed_whatsapp: bool = True
    is_subscribed_sms: bool = True


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    status: str | None = None
    lead_score: int | None = None
    tags: list[str] | None = None
    custom_fields_json: dict | None = None
    is_subscribed_email: bool | None = None
    is_subscribed_whatsapp: bool | None = None
    is_subscribed_sms: bool | None = None


class LeadResponse(LeadBase):
    id: UUID
    workspace_id: UUID
    full_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CSVPreviewRequest(BaseModel):
    csv_content: str


class CSVPreviewResponse(BaseModel):
    headers: list[str]
    sample_rows: list[dict[str, str]]
    suggested_mappings: dict[str, str]
    total_rows: int


class CSVImportStartRequest(BaseModel):
    csv_content: str
    filename: str = "leads_import.csv"
    field_mappings: dict[str, str]  # CSV Header -> Lead Field Name


class CSVImportJobResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    filename: str
    total_rows: int
    processed_rows: int
    successful_rows: int
    failed_rows: int
    duplicate_rows: int
    status: str
    error_log_json: list
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
