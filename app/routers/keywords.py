from fastapi import APIRouter, HTTPException

from app.schemas.keywords import (
    KeywordRequest,
    KeywordResult,
)
from app.services.keyword_service import (
    keyword_service,
)


router = APIRouter(
    prefix="/api/v1/keywords",
    tags=["Keywords"],
)


@router.post(
    "",
    response_model=KeywordResult,
)
async def create_keyword_strategy(
    request: KeywordRequest,
) -> KeywordResult:
    try:
        return await keyword_service.build_strategy(
            request
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
