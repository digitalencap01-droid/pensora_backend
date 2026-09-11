from fastapi import (
    APIRouter,
    HTTPException,
)

from app.schemas.html import (
    HTMLRenderRequest,
    HTMLRenderResult,
)
from app.services.html_service import (
    html_service,
)


router = APIRouter(
    prefix="/api/v1/html",
    tags=["HTML"],
)


@router.post(
    "/render",
    response_model=HTMLRenderResult,
)
async def render_article_html(
    request: HTMLRenderRequest,
) -> HTMLRenderResult:
    try:
        return html_service.render(
            request
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
