from fastapi import APIRouter, HTTPException

from app.schemas.content_brief import (
    ContentBriefRequest,
    ContentBriefResult,
)
from app.services.content_brief_service import (
    content_brief_service,
)


router = APIRouter(
    prefix="/api/v1/content-brief",
    tags=["Content Brief"],
)


@router.post(
    "",
    response_model=ContentBriefResult,
)
async def create_content_brief(
    request: ContentBriefRequest,
) -> ContentBriefResult:
    try:
        return await content_brief_service.create_brief(
            request
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
