from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
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


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_leads_workspace_email"),
        Index("idx_leads_workspace_status", "workspace_id", "status"),
        Index("idx_leads_workspace_score", "workspace_id", "lead_score"),
        Index("idx_leads_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    first_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    lead_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="new", index=True
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual", index=True
    )
    custom_fields_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_subscribed_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_subscribed_whatsapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_subscribed_sms: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    activities: Mapped[list[LeadActivity]] = relationship(
        "LeadActivity", back_populates="lead", cascade="all, delete-orphan"
    )


class LeadActivity(TimestampMixin, Base):
    __tablename__ = "lead_activities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    lead_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    lead: Mapped[Lead] = relationship("Lead", back_populates="activities")


class LeadImportJob(TimestampMixin, Base):
    __tablename__ = "lead_import_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )
    field_mappings_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    error_log_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
