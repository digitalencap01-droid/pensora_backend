from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.schemas.article import ArticleResult
from app.schemas.content_brief import (
    ArticleType,
    ContentBriefResult,
    ToneType,
)
from app.schemas.html import HTMLRenderResult
from app.schemas.keywords import (
    ContentGoal,
    KeywordResult,
)
from app.schemas.research import (
    Freshness,
    ResearchResult,
)
from app.schemas.seo import (
    AuthorInfo,
    SchemaType,
    SEOResult,
)


class ContentGenerateRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
    )
    country_code: str = Field(
        default="IN",
        min_length=2,
        max_length=2,
    )
    language: str = Field(
        default="English",
        min_length=2,
        max_length=50,
    )
    language_code: str = Field(
        default="en",
        min_length=2,
        max_length=15,
    )
    text_direction: Literal[
        "ltr",
        "rtl",
    ] = "ltr"
    freshness: Freshness = "30d"
    max_research_queries: int = Field(
        default=4,
        ge=2,
        le=6,
    )
    document_id: UUID | None = Field(
        default=None,
        description=(
            "An uploaded document (from POST "
            "/api/v1/documents/upload) to ground this "
            "article in via RAG, instead of — or alongside "
            "— live web research."
        ),
    )
    image_batch_id: UUID | None = Field(
        default=None,
        description=(
            "An uploaded image batch (from POST "
            "/api/v1/images/upload) to ground this article "
            "in via vision analysis, instead of — or "
            "alongside — live web research. Mutually "
            "exclusive with document_id."
        ),
    )
    use_web_research: bool = Field(
        default=True,
        description=(
            "When document_id or image_batch_id is set, "
            "whether to also run live web research "
            "alongside it. Ignored (always treated as True) "
            "when neither is set."
        ),
    )
    article_type: ArticleType = "blog"
    tone: ToneType = "professional"
    target_audience: str | None = Field(
        default=None,
        max_length=500,
    )
    content_goal: ContentGoal = (
        "organic_traffic"
    )
    target_word_count: int = Field(
        default=2000,
        ge=600,
        le=6000,
    )
    call_to_action: str | None = Field(
        default=None,
        max_length=500,
    )
    additional_instructions: str | None = Field(
        default=None,
        max_length=1500,
    )
    brand_name: str | None = Field(
        default=None,
        max_length=200,
    )
    site_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )
    site_url: HttpUrl | None = None
    article_path_prefix: str = "/blog"
    authors: list[AuthorInfo] = Field(
        default_factory=list,
    )
    publisher_name: str | None = Field(
        default=None,
        max_length=200,
    )
    publisher_url: HttpUrl | None = None
    publisher_logo_url: HttpUrl | None = None
    featured_image_urls: list[
        HttpUrl
    ] = Field(
        default_factory=list,
    )
    featured_image_alt: str | None = Field(
        default=None,
        max_length=500,
    )
    # Separate from featured_image_urls — see SEORequest.thumbnail_image_url.
    thumbnail_image_url: HttpUrl | None = None
    slug_override: str | None = Field(
        default=None,
        max_length=200,
    )
    schema_type_override: (
        SchemaType | None
    ) = None
    date_published: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    date_modified: datetime | None = None
    indexable: bool = True
    include_sources: bool = True
    save_html_file: bool = True

    @field_validator(
        "country_code"
    )
    @classmethod
    def normalize_country_code(
        cls,
        value: str,
    ) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def check_single_grounding_source(self):
        if self.document_id and self.image_batch_id:
            raise ValueError(
                "document_id and image_batch_id are "
                "mutually exclusive — ground the article "
                "in one or the other, not both."
            )
        return self

    @property
    def effective_site_name(self) -> str:
        # site_name is optional on the request — fall back to
        # brand_name, then a generic placeholder, so SEO metadata
        # generation always has something to work with.
        return (
            self.site_name
            or self.brand_name
            or "My Blog"
        )

    @property
    def effective_site_url(self) -> HttpUrl:
        return self.site_url or HttpUrl(
            "https://example.com"
        )


class ContentGenerateResult(BaseModel):
    project_id: UUID
    article_id: UUID
    article_version: int
    research: ResearchResult
    keywords: KeywordResult
    content_brief: ContentBriefResult
    article: ArticleResult
    seo: SEOResult
    html: HTMLRenderResult
