from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UploadedImageSummary(BaseModel):
    id: UUID
    url: str
    order_index: int
    width: int | None
    height: int | None


class ImageBatchUploadResult(BaseModel):
    batch_id: UUID
    image_count: int
    status: str
    created_at: datetime
    images: list[UploadedImageSummary]


class ImageResearchRequest(BaseModel):
    batch_id: UUID
    topic: str
    language: str = "English"


class ImageAnalysisAI(BaseModel):
    description: str
    notable_details: list[str]
    suggested_caption: str
