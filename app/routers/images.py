from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from app.db.repository import content_repository
from app.schemas.image_upload import (
    ImageBatchUploadResult,
    UploadedImageSummary,
)
from app.services.document_service import (
    DocumentProcessingError,
)
from app.services.image_upload_service import (
    image_upload_service,
)


router = APIRouter(
    prefix="/api/v1/images",
    tags=["Images"],
)


@router.post(
    "/upload",
    response_model=ImageBatchUploadResult,
)
async def upload_images(
    files: list[UploadFile] = File(...),
) -> ImageBatchUploadResult:
    prepared = [
        (
            file.filename or "image",
            await file.read(),
            file.content_type
            or "application/octet-stream",
        )
        for file in files
    ]

    try:
        batch = (
            await image_upload_service
            .process_batch_upload(
                files=prepared,
            )
        )
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    images = await content_repository.list_batch_images(
        batch_id=batch.id,
    )

    return ImageBatchUploadResult(
        batch_id=batch.id,
        image_count=batch.image_count,
        status=batch.status,
        created_at=batch.created_at,
        images=[
            UploadedImageSummary(
                id=image.id,
                url=image.public_url,
                order_index=image.order_index,
                width=image.width,
                height=image.height,
            )
            for image in images
        ],
    )


@router.put(
    "/{image_id}",
    response_model=UploadedImageSummary,
)
async def replace_image(
    image_id: UUID,
    file: UploadFile = File(...),
) -> UploadedImageSummary:
    content = await file.read()

    try:
        image = await image_upload_service.replace_image(
            image_id=image_id,
            content=content,
        )
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return UploadedImageSummary(
        id=image.id,
        url=image.public_url,
        order_index=image.order_index,
        width=image.width,
        height=image.height,
    )
