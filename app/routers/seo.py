from fastapi import (
    APIRouter,
    HTTPException,
)

from app.schemas.seo import (
    SEORequest,
    SEOResult,
)
from app.services.seo_service import (
    seo_service,
)


router = APIRouter(
    prefix="/api/v1/seo",
    tags=["SEO"],
)


@router.post(
    "/generate",
    response_model=SEOResult,
)
async def generate_seo(
    request: SEORequest,
) -> SEOResult:
    try:
        return await seo_service.generate_seo(
            request
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
