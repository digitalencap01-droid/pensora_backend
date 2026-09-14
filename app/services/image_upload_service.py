from __future__ import annotations

import io
from uuid import UUID, uuid4

from PIL import Image

from app.core.config import settings
from app.db.models import ImageBatch, UploadedImageRecord
from app.services.document_service import (
    DocumentProcessingError,
    document_service,
)


SUPPORTED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


class ImageUploadService:
    async def process_batch_upload(
        self,
        files: list[tuple[str, bytes, str]],
    ) -> ImageBatch:
        from app.db.repository import content_repository

        if not files:
            raise DocumentProcessingError(
                "No images were uploaded."
            )

        if len(files) > settings.image_batch_max_count:
            raise DocumentProcessingError(
                "Too many images in one batch. Maximum is "
                f"{settings.image_batch_max_count}."
            )

        prepared: list[
            tuple[str, bytes, str, int, int]
        ] = []

        for filename, content, content_type in files:
            (
                normalized_bytes,
                normalized_content_type,
                width,
                height,
            ) = self._validate_and_normalize(
                filename=filename,
                content=content,
            )

            prepared.append(
                (
                    filename,
                    normalized_bytes,
                    normalized_content_type,
                    width,
                    height,
                )
            )

        batch_id = uuid4()

        uploaded: list[
            tuple[str, str, str, str, int, int, int]
        ] = []

        for index, (
            filename,
            normalized_bytes,
            content_type,
            width,
            height,
        ) in enumerate(prepared):
            extension = content_type.split("/")[-1]
            storage_path = (
                f"image-batches/{batch_id}/"
                f"{index}.{extension}"
            )

            await document_service.upload_bytes(
                bucket=settings.document_images_bucket,
                storage_path=storage_path,
                content=normalized_bytes,
                content_type=content_type,
            )

            public_url = (
                f"{settings.supabase_url}"
                "/storage/v1/object/public/"
                f"{settings.document_images_bucket}/"
                f"{storage_path}"
            )

            uploaded.append(
                (
                    filename,
                    storage_path,
                    public_url,
                    content_type,
                    width,
                    height,
                    len(normalized_bytes),
                )
            )

        return await content_repository.save_image_batch(
            batch_id=batch_id,
            storage_bucket=(
                settings.document_images_bucket
            ),
            images=uploaded,
        )

    async def replace_image(
        self,
        image_id: UUID,
        content: bytes,
    ) -> UploadedImageRecord:
        from app.db.repository import content_repository

        existing = await content_repository.get_uploaded_image(
            image_id=image_id,
        )

        if existing is None:
            raise DocumentProcessingError(
                "Uploaded image not found."
            )

        (
            normalized_bytes,
            content_type,
            width,
            height,
        ) = self._validate_and_normalize(
            filename="replacement.png",
            content=content,
        )

        # A new path (not overwriting the old object in place) so
        # the URL changes — otherwise a CDN/browser could keep
        # showing the old bytes for a URL it already cached.
        storage_path = (
            f"image-batches/"
            f"{existing.batch_id}/"
            f"{existing.order_index}-{uuid4().hex[:8]}.png"
        )

        await document_service.upload_bytes(
            bucket=settings.document_images_bucket,
            storage_path=storage_path,
            content=normalized_bytes,
            content_type=content_type,
        )

        public_url = (
            f"{settings.supabase_url}"
            "/storage/v1/object/public/"
            f"{settings.document_images_bucket}/"
            f"{storage_path}"
        )

        return await content_repository.update_uploaded_image(
            image_id=existing.id,
            storage_path=storage_path,
            public_url=public_url,
            content_type=content_type,
            width=width,
            height=height,
            file_size_bytes=len(normalized_bytes),
        )

    def _validate_and_normalize(
        self,
        filename: str,
        content: bytes,
    ) -> tuple[bytes, str, int, int]:
        extension = (
            filename.rsplit(".", 1)[-1].lower()
            if "." in filename
            else ""
        )

        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(
                f"Unsupported image type '.{extension}' "
                f"for '{filename}'. Supported types: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            )

        max_bytes = (
            settings.image_max_file_size_mb * 1024 * 1024
        )

        if len(content) > max_bytes:
            raise DocumentProcessingError(
                f"'{filename}' is too large. Maximum size "
                f"is {settings.image_max_file_size_mb} MB "
                "per image."
            )

        if len(content) == 0:
            raise DocumentProcessingError(
                f"'{filename}' is empty."
            )

        try:
            with Image.open(
                io.BytesIO(content)
            ) as image:
                width, height = image.size

                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert(
                        "RGBA"
                        if "A" in image.mode
                        else "RGB"
                    )

                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                return (
                    buffer.getvalue(),
                    "image/png",
                    width,
                    height,
                )
        except DocumentProcessingError:
            raise
        except Exception as exc:
            raise DocumentProcessingError(
                f"Could not read '{filename}' as an image."
            ) from exc


image_upload_service = ImageUploadService()
