from fastapi import APIRouter, HTTPException

from app.schemas.research import (
    ResearchRequest,
    ResearchResult,
)
from app.services.research_service import (
    research_service,
)


router = APIRouter(
    prefix="/api/v1/research",
    tags=["Research"],
)


@router.post(
    "",
    response_model=ResearchResult,
)
async def research_topic(
    request: ResearchRequest,
) -> ResearchResult:
    try:
        return await research_service.research(
            request
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
