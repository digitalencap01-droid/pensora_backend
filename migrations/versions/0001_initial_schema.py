"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-11 00:00:00.000000

Creates every table this app owns, straight from the SQLAlchemy
models (app/db/models.py) rather than hand-transcribed op.* calls —
this is the very first migration for this project, so there's no
prior revision history to stay consistent with.

This schema runs without per-request authentication (see
app/core/rate_limit.py and README.md): there is no user_id column and
no Row-Level Security policy anywhere. If auth is reintroduced later,
add a follow-up migration for both rather than editing this one.

Requires the pgvector extension for document_chunks.embedding. If
`CREATE EXTENSION` fails because the migration role lacks privileges,
run that one statement manually first, then re-run
`alembic upgrade head`.
"""
from typing import Sequence, Union

from alembic import op

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema};"
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    bind = op.get_bind()
    Base.metadata.create_all(bind, checkfirst=True)

    op.execute(
        "CREATE INDEX IF NOT EXISTS "
        "ix_document_chunks_embedding_hnsw "
        f"ON {settings.db_schema}.document_chunks "
        "USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind, checkfirst=True)
