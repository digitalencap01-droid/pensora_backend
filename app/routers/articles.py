from fastapi import APIRouter, HTTPException

from app.schemas.article import (
    ArticleRequest,
    ArticleResult,
)
from app.services.article_service import (
    article_service,
)


router = APIRouter(
    prefix="/api/v1/articles",
    tags=["Articles"],
)


@router.post(
    "/generate",
    response_model=ArticleResult,
)
async def generate_article(
    request: ArticleRequest,
) -> ArticleResult:
    try:
        return await article_service.generate_article(
            request
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
