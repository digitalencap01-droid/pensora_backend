from __future__ import annotations

import io
from dataclasses import dataclass
from uuid import uuid4

import httpx
from docx import Document as DocxDocument
from PIL import Image
from pypdf import PdfReader

from app.core.config import settings
from app.db.models import UploadedDocument
from app.services.openai_service import openai_service


@dataclass
class ExtractedImage:
    content: bytes
    content_type: str
    width: int
    height: int
    page_number: int | None


SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
    "txt": "text/plain",
    "md": "text/markdown",
}

_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 150


class DocumentProcessingError(Exception):
    pass


class DocumentService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.embedding_model = settings.openai_embedding_model

    async def process_upload(
        self,
        filename: str,
        content: bytes,
    ) -> UploadedDocument:
        from app.db.repository import content_repository

        extension = self.validate_upload(
            filename=filename,
            file_size_bytes=len(content),
        )

        pages = self.extract_pages(extension, content)
        char_count = sum(len(page) for page in pages)

        page_chunks = self.chunk_pages(pages)

        if not page_chunks:
            raise DocumentProcessingError(
                "No usable content could be extracted "
                "from this document."
            )

        texts = [chunk_text for chunk_text, _ in page_chunks]
        embeddings = await self.embed_texts(texts)

        document_id = uuid4()
        storage_path = f"documents/{document_id}.{extension}"

        await self.upload_to_storage(
            storage_path=storage_path,
            content=content,
            content_type=_CONTENT_TYPES[extension],
        )

        chunks = [
            (chunk_text, page_number, embedding)
            for (chunk_text, page_number), embedding in zip(
                page_chunks, embeddings, strict=True
            )
        ]

        document = (
            await content_repository.save_document_with_chunks(
                document_id=document_id,
                filename=filename,
                file_type=extension,
                storage_bucket=settings.document_storage_bucket,
                storage_path=storage_path,
                file_size_bytes=len(content),
                char_count=char_count,
                page_count=(
                    len(pages) if extension == "pdf" else None
                ),
                chunks=chunks,
            )
        )

        try:
            extracted_images = self.extract_images(
                extension, content
            )
        except Exception:
            # Image extraction is a bonus, not core to the upload —
            # a malformed embedded image shouldn't fail the whole
            # document (the text/chunks are already saved above).
            extracted_images = []

        if extracted_images:
            uploaded_images = []

            for index, image in enumerate(extracted_images):
                image_storage_path = (
                    f"documents/{document_id}/images/"
                    f"{index}.png"
                )

                await self.upload_bytes(
                    bucket=settings.document_images_bucket,
                    storage_path=image_storage_path,
                    content=image.content,
                    content_type=image.content_type,
                )

                public_url = (
                    f"{settings.supabase_url}"
                    "/storage/v1/object/public/"
                    f"{settings.document_images_bucket}/"
                    f"{image_storage_path}"
                )

                uploaded_images.append(
                    (
                        image_storage_path,
                        public_url,
                        image.content_type,
                        image.width,
                        image.height,
                        len(image.content),
                        image.page_number,
                    )
                )

            await content_repository.save_document_images(
                document_id=document.id,
                storage_bucket=(
                    settings.document_images_bucket
                ),
                images=uploaded_images,
            )

        return document

    def validate_upload(
        self,
        filename: str,
        file_size_bytes: int,
    ) -> str:
        extension = (
            filename.rsplit(".", 1)[-1].lower()
            if "." in filename
            else ""
        )

        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(
                f"Unsupported file type '.{extension}'. "
                "Supported types: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            )

        max_bytes = (
            settings.document_max_file_size_mb * 1024 * 1024
        )

        if file_size_bytes > max_bytes:
            raise DocumentProcessingError(
                "File is too large. Maximum size is "
                f"{settings.document_max_file_size_mb} MB."
            )

        if file_size_bytes == 0:
            raise DocumentProcessingError(
                "The uploaded file is empty."
            )

        return extension

    def extract_pages(
        self,
        extension: str,
        content: bytes,
    ) -> list[str]:
        if extension == "pdf":
            return self._extract_pdf_pages(content)
        if extension == "docx":
            return [self._extract_docx_text(content)]
        return [self._extract_plain_text(content)]

    def _extract_pdf_pages(
        self,
        content: bytes,
    ) -> list[str]:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as exc:
            raise DocumentProcessingError(
                "Could not read this PDF file."
            ) from exc

        pages = []

        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(text)

        if not pages:
            raise DocumentProcessingError(
                "Could not extract any text from this PDF. "
                "It may be a scanned or image-only PDF."
            )

        return pages

    def _extract_docx_text(
        self,
        content: bytes,
    ) -> str:
        try:
            document = DocxDocument(io.BytesIO(content))
        except Exception as exc:
            raise DocumentProcessingError(
                "Could not read this Word document."
            ) from exc

        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        text = "\n\n".join(paragraphs)

        if not text.strip():
            raise DocumentProcessingError(
                "Could not extract any text from this document."
            )

        return text

    def _extract_plain_text(
        self,
        content: bytes,
    ) -> str:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        if not text.strip():
            raise DocumentProcessingError(
                "The uploaded file appears to be empty."
            )

        return text

    def chunk_pages(
        self,
        pages: list[str],
    ) -> list[tuple[str, int | None]]:
        has_page_numbers = len(pages) > 1

        chunks: list[tuple[str, int | None]] = []

        for page_index, page_text in enumerate(pages, start=1):
            for chunk_text in self._chunk_text(page_text):
                chunks.append(
                    (
                        chunk_text,
                        page_index if has_page_numbers else None,
                    )
                )

        return chunks

    def _chunk_text(self, text: str) -> list[str]:
        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            candidate = (
                f"{current}\n\n{paragraph}"
                if current
                else paragraph
            )

            if len(candidate) <= _CHUNK_SIZE:
                current = candidate
                continue

            if current:
                chunks.append(current)
                current = ""

            if len(paragraph) <= _CHUNK_SIZE:
                current = paragraph
                continue

            # A single paragraph longer than the chunk size — hard
            # split it with overlap rather than dropping content.
            start = 0
            while start < len(paragraph):
                end = start + _CHUNK_SIZE
                chunks.append(paragraph[start:end])
                start = end - _CHUNK_OVERLAP

        if current:
            chunks.append(current)

        return chunks

    def extract_images(
        self,
        extension: str,
        content: bytes,
    ) -> list[ExtractedImage]:
        if extension == "pdf":
            return self._extract_pdf_images(content)
        if extension == "docx":
            return self._extract_docx_images(content)
        return []

    def _extract_pdf_images(
        self,
        content: bytes,
    ) -> list[ExtractedImage]:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception:
            return []

        images: list[ExtractedImage] = []

        for page_index, page in enumerate(
            reader.pages, start=1
        ):
            if (
                len(images)
                >= settings.document_image_max_count
            ):
                break

            try:
                page_images = page.images
            except Exception:
                continue

            for image_file in page_images:
                if (
                    len(images)
                    >= settings.document_image_max_count
                ):
                    break

                normalized = self._normalize_image(
                    image_file.data
                )

                if normalized is None:
                    continue

                image_bytes, width, height = normalized

                images.append(
                    ExtractedImage(
                        content=image_bytes,
                        content_type="image/png",
                        width=width,
                        height=height,
                        page_number=page_index,
                    )
                )

        return images

    def _extract_docx_images(
        self,
        content: bytes,
    ) -> list[ExtractedImage]:
        try:
            document = DocxDocument(io.BytesIO(content))
        except Exception:
            return []

        images: list[ExtractedImage] = []

        for part in document.part.related_parts.values():
            if (
                len(images)
                >= settings.document_image_max_count
            ):
                break

            content_type = getattr(
                part, "content_type", ""
            )

            if not content_type.startswith("image/"):
                continue

            normalized = self._normalize_image(part.blob)

            if normalized is None:
                continue

            image_bytes, width, height = normalized

            images.append(
                ExtractedImage(
                    content=image_bytes,
                    content_type="image/png",
                    width=width,
                    height=height,
                    page_number=None,
                )
            )

        return images

    def _normalize_image(
        self,
        raw_bytes: bytes,
    ) -> tuple[bytes, int, int] | None:
        # Re-encodes every extracted image to PNG. Some embedded PDF
        # image encodings (CCITT fax, indexed CMYK, ...) or DOCX
        # vector formats (WMF/EMF) can't be rendered directly by a
        # browser — decoding via Pillow and re-saving normalizes all
        # of that into something every browser can show.
        try:
            with Image.open(
                io.BytesIO(raw_bytes)
            ) as image:
                width, height = image.size

                min_dimension = (
                    settings
                    .document_image_min_dimension_px
                )

                if (
                    width < min_dimension
                    or height < min_dimension
                ):
                    return None

                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert(
                        "RGBA"
                        if "A" in image.mode
                        else "RGB"
                    )

                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                return buffer.getvalue(), width, height
        except Exception:
            return None

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )

        return [item.embedding for item in response.data]

    async def upload_to_storage(
        self,
        *,
        storage_path: str,
        content: bytes,
        content_type: str,
    ) -> None:
        await self.upload_bytes(
            bucket=settings.document_storage_bucket,
            storage_path=storage_path,
            content=content,
            content_type=content_type,
        )

    async def upload_bytes(
        self,
        *,
        bucket: str,
        storage_path: str,
        content: bytes,
        content_type: str,
    ) -> None:
        if not settings.supabase_service_role_key:
            raise DocumentProcessingError(
                "Document upload is not configured: "
                "SUPABASE_SERVICE_ROLE_KEY is not set."
            )

        url = (
            f"{settings.supabase_url}/storage/v1/object/"
            f"{bucket}/{storage_path}"
        )

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                content=content,
                headers={
                    "Authorization": (
                        "Bearer "
                        f"{settings.supabase_service_role_key}"
                    ),
                    "apikey": (
                        settings.supabase_service_role_key
                    ),
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
            )

        if response.status_code >= 400:
            raise DocumentProcessingError(
                "Failed to store the uploaded file "
                f"({response.status_code}): {response.text}"
            )


document_service = DocumentService()
