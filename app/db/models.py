from __future__ import annotations

from datetime import datetime
from uuid import (
    UUID,
    uuid4,
)

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID as PG_UUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import (
    Base,
    TimestampMixin,
)


# text-embedding-3-small's native dimensionality — see
# app/services/document_service.py.
EMBEDDING_DIMENSIONS = 1536


class ContentProject(
    TimestampMixin,
    Base,
):
    __tablename__ = "content_projects"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    topic: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    article_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    tone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    content_goal: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="created",
        index=True,
    )
    current_stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    request_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    error_stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    webflow_item_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    webflow_publish_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )


class ResearchRun(
    TimestampMixin,
    Base,
):
    __tablename__ = "research_runs"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name=(
                "uq_research_runs_project_version"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )


class KeywordStrategyRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "keyword_strategies"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name=(
                "uq_keyword_strategies_"
                "project_version"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    primary_keyword: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    search_intent: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )


class ContentBriefRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "content_briefs"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name=(
                "uq_content_briefs_project_version"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    recommended_title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    target_word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )


class ArticleRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "articles"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    current_version_number: Mapped[int] = (
        mapped_column(
            Integer,
            nullable=False,
            default=1,
        )
    )


class ArticleVersionRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "article_versions"

    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "version_number",
            name=(
                "uq_article_versions_"
                "article_version"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    article_markdown: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )


class SEOMetadataRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "seo_metadata"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name=(
                "uq_seo_metadata_project_version"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    article_version_id: Mapped[UUID] = (
        mapped_column(
            PG_UUID(as_uuid=True),
            ForeignKey(
                "article_versions.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    canonical_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    readiness_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )


class GeneratedFileRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "generated_files"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    article_version_id: Mapped[UUID] = (
        mapped_column(
            PG_UUID(as_uuid=True),
            ForeignKey(
                "article_versions.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )
    seo_metadata_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "seo_metadata.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="html",
    )
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    relative_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    full_html: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    article_html: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


class UploadedDocument(
    TimestampMixin,
    Base,
):
    __tablename__ = "uploaded_documents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    storage_bucket: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    char_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="processing",
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class DocumentChunkRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "document_chunks"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name=(
                "uq_document_chunks_"
                "document_chunk_index"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "uploaded_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=False,
    )


class DocumentImageRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "document_images"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "uploaded_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    storage_bucket: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    public_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


class ImageBatch(
    TimestampMixin,
    Base,
):
    __tablename__ = "image_batches"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_projects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    image_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ready",
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


# Single global LinkedIn connection for this app (not per-user) — this
# app runs without per-request authentication, so publishing to
# LinkedIn authenticates as whichever account was last connected via
# GET /api/v1/linkedin/connect. Same singleton-row pattern as
# WebflowConfig below.
class LinkedInConnection(
    TimestampMixin,
    Base,
):
    __tablename__ = "linkedin_connections"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    linkedin_member_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    linkedin_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )
    linkedin_email: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )
    access_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    refresh_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    scope: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


# Single global Webflow CMS destination for this app (not per-user) —
# the auth token itself lives server-side in settings.webflow_token,
# never in the database.
class WebflowConfig(
    TimestampMixin,
    Base,
):
    __tablename__ = "webflow_config"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    site_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    site_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    collection_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    collection_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    title_field: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="name",
    )
    slug_field: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="slug",
    )
    body_field: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="post-body",
    )
    summary_field: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="post-summary",
    )
    main_image_field: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    thumbnail_field: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


class UploadedImageRecord(
    TimestampMixin,
    Base,
):
    __tablename__ = "uploaded_images"

    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "order_index",
            name=(
                "uq_uploaded_images_batch_order_index"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "image_batches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    storage_bucket: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    public_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
