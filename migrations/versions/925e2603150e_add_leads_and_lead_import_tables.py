"""Add leads and lead import tables

Revision ID: 925e2603150e
Revises: 4ca1e624b914
Create Date: 2026-09-11 16:30:54.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '925e2603150e'
down_revision: Union[str, Sequence[str], None] = '4ca1e624b914'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('first_name', sa.String(length=150), nullable=True),
        sa.Column('last_name', sa.String(length=150), nullable=True),
        sa.Column('full_name', sa.String(length=300), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True, index=True),
        sa.Column('phone', sa.String(length=50), nullable=True, index=True),
        sa.Column('company_name', sa.String(length=200), nullable=True),
        sa.Column('job_title', sa.String(length=150), nullable=True),
        sa.Column('lead_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='new', index=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='manual', index=True),
        sa.Column('custom_fields_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('is_subscribed_email', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_subscribed_whatsapp', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_subscribed_sms', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('workspace_id', 'email', name='uq_leads_workspace_email')
    )
    op.create_index('idx_leads_workspace_status', 'leads', ['workspace_id', 'status'])
    op.create_index('idx_leads_workspace_score', 'leads', ['workspace_id', 'lead_score'])
    op.create_index('idx_leads_workspace_created', 'leads', ['workspace_id', 'created_at'])

    # 2. lead_activities table
    op.create_table(
        'lead_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('activity_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 3. lead_import_jobs table
    op.create_table(
        'lead_import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending', index=True),
        sa.Column('field_mappings_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_log_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('lead_import_jobs')
    op.drop_table('lead_activities')
    op.drop_index('idx_leads_workspace_created', table_name='leads')
    op.drop_index('idx_leads_workspace_score', table_name='leads')
    op.drop_index('idx_leads_workspace_status', table_name='leads')
    op.drop_table('leads')
