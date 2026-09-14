from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from app.core.exceptions import (
    ContentPipelineError,
)
from app.core.rate_limit import (
    enforce_generate_rate_limit,
)
from app.schemas.content import (
    ContentGenerateRequest,
    ContentGenerateResult,
)
from app.services.content_pipeline_service import (
    content_pipeline_service,
)


router = APIRouter(
    prefix="/api/v1/content",
    tags=["Content"],
)


@router.post(
    "/generate",
    response_model=ContentGenerateResult,
    dependencies=[
        Depends(enforce_generate_rate_limit)
    ],
)
async def generate_content(
    request: ContentGenerateRequest,
) -> ContentGenerateResult:
    try:
        return (
            await content_pipeline_service.generate(
                request=request,
            )
        )
    except ContentPipelineError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "stage": exc.stage,
                "message": exc.message,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "stage": "unknown",
                "message": str(exc),
            },
        ) from exc
