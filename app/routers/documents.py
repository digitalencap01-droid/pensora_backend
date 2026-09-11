from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.repository import content_repository
from app.schemas.document import (
    DocumentImageListResult,
    DocumentImageSummary,
    DocumentListResult,
    DocumentSummary,
    DocumentUploadResult,
)
from app.services.document_service import (
    DocumentProcessingError,
    document_service,
)


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentUploadResult,
)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DocumentUploadResult:
    content = await file.read()

    try:
        document = await document_service.process_upload(
            session=session,
            filename=file.filename or "document",
            content=content,
        )
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    images = await content_repository.list_document_images(
        session=session,
        document_id=document.id,
    )

    return DocumentUploadResult(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size_bytes=document.file_size_bytes,
        char_count=document.char_count,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        status=document.status,
        created_at=document.created_at,
        images=[
            _to_image_summary(image)
            for image in images
        ],
    )


@router.get(
    "/{document_id}/images",
    response_model=DocumentImageListResult,
)
async def list_document_images(
    document_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DocumentImageListResult:
    document = await content_repository.get_document(
        session=session,
        document_id=document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    images = await content_repository.list_document_images(
        session=session,
        document_id=document_id,
    )

    return DocumentImageListResult(
        images=[
            _to_image_summary(image)
            for image in images
        ]
    )


def _to_image_summary(
    image,
) -> DocumentImageSummary:
    return DocumentImageSummary(
        id=image.id,
        url=image.public_url,
        page_number=image.page_number,
        width=image.width,
        height=image.height,
    )


@router.get(
    "",
    response_model=DocumentListResult,
)
async def list_documents(
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DocumentListResult:
    documents = await content_repository.list_documents(
        session=session,
    )

    return DocumentListResult(
        documents=[
            DocumentSummary(
                id=document.id,
                filename=document.filename,
                file_type=document.file_type,
                char_count=document.char_count,
                page_count=document.page_count,
                chunk_count=document.chunk_count,
                status=document.status,
                created_at=document.created_at,
            )
            for document in documents
        ]
    )
