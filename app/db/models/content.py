from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.models.enums import ApprovalStatusEnum, ContentStatusEnum, ContentTypeEnum


class Content(TimestampMixin, Base):
    __tablename__ = "contents"

    __table_args__ = (
        CheckConstraint(
            "type IN ('blog', 'email', 'whatsapp', 'social', 'ad')",
            name="ck_contents_type_valid",
        ),
        CheckConstraint(
            "status IN ('idea', 'draft', 'generated', 'in_review', 'changes_requested', "
            "'approved', 'scheduled', 'publishing', 'published', 'failed', 'archived')",
            name="ck_contents_status_valid",
        ),
        Index("idx_contents_workspace_status", "workspace_id", "status"),
        Index("idx_contents_workspace_type", "workspace_id", "type"),
        Index("idx_contents_workspace_created_at", "workspace_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ContentTypeEnum.BLOG.value
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ContentStatusEnum.DRAFT.value
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Staged circular FK references to content_versions to prevent migration deadlock
    current_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_contents_current_version_id_content_versions",
        ),
        nullable=True,
    )
    approved_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_contents_approved_version_id_content_versions",
        ),
        nullable=True,
    )
    published_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "content_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_contents_published_version_id_content_versions",
        ),
        nullable=True,
    )
    
    is_archived: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)

    # Relationships
    versions: Mapped[list[ContentVersion]] = relationship(
        "ContentVersion",
        back_populates="content",
        cascade="all, delete-orphan",
        foreign_keys="[ContentVersion.content_id]",
    )
    seo_record: Mapped[ContentSEO | None] = relationship(
        "ContentSEO",
        back_populates="content",
        uselist=False,
        cascade="all, delete-orphan",
    )
    publications: Mapped[list[ContentPublication]] = relationship(
        "ContentPublication", back_populates="content", cascade="all, delete-orphan"
    )
    approval_requests: Mapped[list[ContentApprovalRequest]] = relationship(
        "ContentApprovalRequest", back_populates="content", cascade="all, delete-orphan"
    )


class ContentVersion(TimestampMixin, Base):
    __tablename__ = "content_versions"

    __table_args__ = (
        UniqueConstraint(
            "content_id",
            "version_number",
            name="uq_content_versions_content_version",
        ),
        Index("idx_content_versions_workspace_content", "workspace_id", "content_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    content: Mapped[Content] = relationship(
        "Content", back_populates="versions", foreign_keys=[content_id]
    )


class ContentSEO(TimestampMixin, Base):
    __tablename__ = "content_seo"

    __table_args__ = (
        CheckConstraint(
            "seo_score BETWEEN 0 AND 100", name="ck_content_seo_seo_score_range"
        ),
        CheckConstraint(
            "readability_score BETWEEN 0 AND 100",
            name="ck_content_seo_readability_score_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    focus_keyword: Mapped[str | None] = mapped_column(String(200), nullable=True)
    secondary_keywords: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    seo_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_markup: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    seo_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    readability_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    content: Mapped[Content] = relationship("Content", back_populates="seo_record")


class ContentPublishTarget(TimestampMixin, Base):
    __tablename__ = "content_publish_targets"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    integration_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    target_details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ContentPublication(TimestampMixin, Base):
    __tablename__ = "content_publications"

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "idempotency_key", name="uq_content_pub_workspace_idempotency"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    external_publish_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    publish_status: Mapped[str] = mapped_column(String(50), nullable=False, default="published")
    provider_response_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    content: Mapped[Content] = relationship("Content", back_populates="publications")


class ContentApprovalRequest(TimestampMixin, Base):
    __tablename__ = "content_approval_requests"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    requested_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ApprovalStatusEnum.PENDING.value
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    content: Mapped[Content] = relationship("Content", back_populates="approval_requests")
