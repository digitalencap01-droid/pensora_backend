"""Add enterprise omnichannel marketing platform models

Revision ID: 4ca1e624b914
Revises: 0001_initial_schema
Create Date: 2026-09-11 16:20:04.225658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4ca1e624b914'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. contents table
    op.create_table(
        'contents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='blog'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('published_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("type IN ('blog', 'email', 'whatsapp', 'social', 'ad')", name='ck_contents_type_valid'),
        sa.CheckConstraint(
            "status IN ('idea', 'draft', 'generated', 'in_review', 'changes_requested', 'approved', 'scheduled', 'publishing', 'published', 'failed', 'archived')",
            name='ck_contents_status_valid'
        )
    )
    op.create_index('idx_contents_workspace_status', 'contents', ['workspace_id', 'status'])
    op.create_index('idx_contents_workspace_type', 'contents', ['workspace_id', 'type'])
    op.create_index('idx_contents_workspace_created_at', 'contents', ['workspace_id', 'created_at'])

    # 2. content_versions table
    op.create_table(
        'content_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('content_id', 'version_number', name='uq_content_versions_content_version')
    )
    op.create_index('idx_content_versions_workspace_content', 'content_versions', ['workspace_id', 'content_id'])

    # Staged FK creation on contents to avoid circular dependency
    op.create_foreign_key('fk_contents_current_version_id_content_versions', 'contents', 'content_versions', ['current_version_id'], ['id'], ondelete='SET NULL', use_alter=True)
    op.create_foreign_key('fk_contents_approved_version_id_content_versions', 'contents', 'content_versions', ['approved_version_id'], ['id'], ondelete='SET NULL', use_alter=True)
    op.create_foreign_key('fk_contents_published_version_id_content_versions', 'contents', 'content_versions', ['published_version_id'], ['id'], ondelete='SET NULL', use_alter=True)

    # 3. content_seo table
    op.create_table(
        'content_seo',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('focus_keyword', sa.String(length=200), nullable=True),
        sa.Column('secondary_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('seo_title', sa.String(length=300), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('canonical_url', sa.Text(), nullable=True),
        sa.Column('og_image', sa.Text(), nullable=True),
        sa.Column('schema_markup', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('seo_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('readability_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('seo_score BETWEEN 0 AND 100', name='ck_content_seo_seo_score_range'),
        sa.CheckConstraint('readability_score BETWEEN 0 AND 100', name='ck_content_seo_readability_score_range')
    )

    # 4. content_publish_targets table
    op.create_table(
        'content_publish_targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('target_details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 5. content_publications table
    op.create_table(
        'content_publications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('external_publish_id', sa.String(length=255), nullable=True),
        sa.Column('published_url', sa.Text(), nullable=True),
        sa.Column('publish_status', sa.String(length=50), nullable=False, server_default='published'),
        sa.Column('provider_response_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('workspace_id', 'idempotency_key', name='uq_content_pub_workspace_idempotency')
    )

    # 6. content_approval_requests table
    op.create_table(
        'content_approval_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 7. scheduled_jobs table
    op.create_table(
        'scheduled_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('job_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending', index=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('job_payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_strategy', sa.String(length=50), nullable=False, server_default='exponential_backoff'),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.String(length=200), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('attempt_count <= max_attempts', name='ck_scheduled_jobs_attempt_count_max'),
        sa.UniqueConstraint('workspace_id', 'idempotency_key', name='uq_scheduled_jobs_workspace_idempotency')
    )
    op.create_index('idx_jobs_due', 'scheduled_jobs', ['workspace_id', 'status', 'scheduled_at', 'next_retry_at'])

    # 8. job_runs table
    op.create_table(
        'job_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scheduled_jobs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 9. job_failures table
    op.create_table(
        'job_failures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scheduled_jobs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('job_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_runs.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('error_type', sa.String(length=200), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('payload_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 10. workspace_integrations table
    op.create_table(
        'workspace_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('provider_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active', index=True),
        sa.Column('encrypted_credentials', sa.Text(), nullable=False),
        sa.Column('settings_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('key_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 11. provider_execution_logs table
    op.create_table(
        'provider_execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('provider', sa.String(length=100), nullable=False, index=True),
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('request_metadata_sanitized', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('response_metadata_sanitized', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 12. message_deliveries table
    op.create_table(
        'message_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('campaign_message_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('channel', sa.String(length=50), nullable=False, index=True),
        sa.Column('provider', sa.String(length=100), nullable=False, index=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('recipient_address_masked', sa.String(length=255), nullable=False),
        sa.Column('external_message_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('workspace_id', 'idempotency_key', name='uq_message_deliveries_workspace_idempotency')
    )
    op.create_index('idx_delivery_workspace_campaign', 'message_deliveries', ['workspace_id', 'campaign_id'])
    op.create_index('idx_delivery_external_message', 'message_deliveries', ['workspace_id', 'external_message_id'])
    op.create_index('idx_delivery_status', 'message_deliveries', ['workspace_id', 'status'])

    # 13. content_metrics table
    op.create_table(
        'content_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('metric_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='system'),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_metrics_workspace_content_time', 'content_metrics', ['workspace_id', 'content_id', 'recorded_at'])

    # 14. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('actor_type', sa.String(length=50), nullable=False, server_default='user', index=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('entity_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('action', sa.String(length=100), nullable=False, index=True),
        sa.Column('before_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('after_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_index('idx_metrics_workspace_content_time', table_name='content_metrics')
    op.drop_table('content_metrics')
    op.drop_index('idx_delivery_status', table_name='message_deliveries')
    op.drop_index('idx_delivery_external_message', table_name='message_deliveries')
    op.drop_index('idx_delivery_workspace_campaign', table_name='message_deliveries')
    op.drop_table('message_deliveries')
    op.drop_table('provider_execution_logs')
    op.drop_table('workspace_integrations')
    op.drop_table('job_failures')
    op.drop_table('job_runs')
    op.drop_index('idx_jobs_due', table_name='scheduled_jobs')
    op.drop_table('scheduled_jobs')
    op.drop_table('content_approval_requests')
    op.drop_table('content_publications')
    op.drop_table('content_publish_targets')
    op.drop_table('content_seo')
    op.drop_constraint('fk_contents_published_version_id_content_versions', 'contents', type_='foreignkey')
    op.drop_constraint('fk_contents_approved_version_id_content_versions', 'contents', type_='foreignkey')
    op.drop_constraint('fk_contents_current_version_id_content_versions', 'contents', type_='foreignkey')
    op.drop_index('idx_content_versions_workspace_content', table_name='content_versions')
    op.drop_table('content_versions')
    op.drop_index('idx_contents_workspace_created_at', table_name='contents')
    op.drop_index('idx_contents_workspace_type', table_name='contents')
    op.drop_index('idx_contents_workspace_status', table_name='contents')
    op.drop_table('contents')
