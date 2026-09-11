from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.article import (
    ArticleResult,
)
from app.schemas.content_brief import (
    ContentBriefResult,
)
from app.schemas.html import (
    HTMLRenderResult,
)
from app.schemas.keywords import (
    KeywordResult,
)
from app.schemas.research import (
    ResearchResult,
)
from app.schemas.seo import (
    SEOResult,
)


class ProjectSummary(BaseModel):
    id: UUID
    topic: str
    status: str
    current_stage: str | None
    article_type: str
    tone: str
    language: str
    country_code: str
    error_stage: str | None
    webflow_item_id: str | None = None
    webflow_publish_status: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectListResult(BaseModel):
    items: list[ProjectSummary]
    total: int
    limit: int
    offset: int


class ProjectDetail(ProjectSummary):
    content_goal: str
    request_payload: dict[str, Any]
    error_message: str | None


class ProjectArtifactsResult(BaseModel):
    project_id: UUID
    research: ResearchResult | None = None
    keywords: KeywordResult | None = None
    content_brief: ContentBriefResult | None = None
    article: ArticleResult | None = None
    seo: SEOResult | None = None
    html: HTMLRenderResult | None = None


class ArticleVersionSummary(BaseModel):
    version_id: UUID
    version_number: int
    word_count: int
    created_at: datetime


class ArticleVersionListResult(BaseModel):
    article_id: UUID
    current_version_number: int
    versions: list[ArticleVersionSummary]


class ArticleVersionDetail(BaseModel):
    article_id: UUID
    version_id: UUID
    version_number: int
    article: ArticleResult


class ArticleUpdateRequest(BaseModel):
    article: ArticleResult


class RegenerateSectionRequest(BaseModel):
    section_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    instructions: str | None = Field(
        default=None,
        max_length=1500,
    )


class ArticleMutationResult(BaseModel):
    project_id: UUID
    article_id: UUID
    article_version_id: UUID
    version_number: int
    article: ArticleResult
    seo: SEOResult
    html: HTMLRenderResult


class RebuildOutputResult(BaseModel):
    project_id: UUID
    article_id: UUID
    version_number: int
    seo: SEOResult
    html: HTMLRenderResult


class UsageSummary(BaseModel):
    total_projects: int
    completed_projects: int
    failed_projects: int
    total_words_written: int
