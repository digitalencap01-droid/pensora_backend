import pytest

from app.core.config import settings
from app.services.document_service import (
    DocumentProcessingError,
    DocumentService,
)


@pytest.fixture
def service() -> DocumentService:
    return DocumentService()


def test_validate_upload_rejects_unsupported_extension(
    service: DocumentService,
) -> None:
    with pytest.raises(DocumentProcessingError):
        service.validate_upload(
            filename="notes.exe",
            file_size_bytes=100,
        )


def test_validate_upload_rejects_oversized_file(
    service: DocumentService,
) -> None:
    with pytest.raises(DocumentProcessingError):
        service.validate_upload(
            filename="report.pdf",
            file_size_bytes=(
                settings.document_max_file_size_mb
                * 1024
                * 1024
                + 1
            ),
        )


def test_validate_upload_rejects_empty_file(
    service: DocumentService,
) -> None:
    with pytest.raises(DocumentProcessingError):
        service.validate_upload(
            filename="report.pdf",
            file_size_bytes=0,
        )


def test_validate_upload_accepts_supported_types(
    service: DocumentService,
) -> None:
    for filename in (
        "report.pdf",
        "report.docx",
        "notes.txt",
        "notes.md",
    ):
        assert (
            service.validate_upload(
                filename=filename,
                file_size_bytes=1024,
            )
            == filename.rsplit(".", 1)[-1]
        )


def test_extract_plain_text_from_txt(
    service: DocumentService,
) -> None:
    pages = service.extract_pages(
        "txt", b"Hello world."
    )

    assert pages == ["Hello world."]


def test_extract_plain_text_rejects_empty_content(
    service: DocumentService,
) -> None:
    with pytest.raises(DocumentProcessingError):
        service.extract_pages("txt", b"   \n\n  ")


def test_chunk_text_packs_short_paragraphs_together(
    service: DocumentService,
) -> None:
    text = "First paragraph.\n\nSecond paragraph."

    chunks = service._chunk_text(text)

    assert chunks == [text]


def test_chunk_text_hard_splits_a_long_paragraph(
    service: DocumentService,
) -> None:
    long_paragraph = "word " * 1000

    chunks = service._chunk_text(long_paragraph)

    assert len(chunks) > 1
    assert all(len(chunk) <= 1200 for chunk in chunks)
    assert long_paragraph.startswith(chunks[0])


def test_chunk_pages_tracks_page_numbers_only_for_multi_page(
    service: DocumentService,
) -> None:
    single_page_chunks = service.chunk_pages(
        ["Only page."]
    )
    assert all(
        page_number is None
        for _, page_number in single_page_chunks
    )

    multi_page_chunks = service.chunk_pages(
        ["Page one.", "Page two."]
    )
    assert [
        page_number
        for _, page_number in multi_page_chunks
    ] == [1, 2]
