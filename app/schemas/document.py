from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentImageSummary(BaseModel):
    id: UUID
    url: str
    page_number: int | None
    width: int | None
    height: int | None


class DocumentUploadResult(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size_bytes: int
    char_count: int
    page_count: int | None
    chunk_count: int
    status: str
    created_at: datetime
    images: list[DocumentImageSummary] = []


class DocumentImageListResult(BaseModel):
    images: list[DocumentImageSummary]


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    file_type: str
    char_count: int
    page_count: int | None
    chunk_count: int
    status: str
    created_at: datetime


class DocumentListResult(BaseModel):
    documents: list[DocumentSummary]


class DocumentChunkMatch(BaseModel):
    chunk_index: int
    page_number: int | None
    content: str


class DocumentResearchRequest(BaseModel):
    document_id: UUID
    topic: str
    language: str = "English"
    max_queries: int = 4
    chunks_per_query: int = 6
