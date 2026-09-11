from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
)

from app.schemas.article import ArticleResult
from app.schemas.content_brief import (
    ContentBriefResult,
)


SchemaType = Literal[
    "Article",
    "BlogPosting",
    "NewsArticle",
]


AuthorType = Literal[
    "Person",
    "Organization",
]


SEOCheckStatus = Literal[
    "pass",
    "warning",
    "fail",
]


class AuthorInfo(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
    )
    author_type: AuthorType = "Person"
    url: HttpUrl | None = None


class SEORequest(BaseModel):
    article: ArticleResult
    brief: ContentBriefResult
    site_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
    )
    site_url: HttpUrl
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
    featured_image_urls: list[HttpUrl] = Field(
        default_factory=list,
    )
    # Distinct from featured_image_urls (the in-article hero/OG
    # image) — some publish targets (e.g. a Webflow CMS collection's
    # required thumbnail field) want a separate thumbnail image.
    # Falls back to the first featured image when not set — see
    # SEOService.generate_seo.
    thumbnail_image_url: HttpUrl | None = None
    slug_override: str | None = Field(
        default=None,
        max_length=200,
    )
    date_published: datetime | None = None
    date_modified: datetime | None = None
    indexable: bool = True
    schema_type_override: SchemaType | None = None


class SEOMetadataAI(BaseModel):
    seo_title: str
    meta_description: str
    social_title: str
    social_description: str


class OpenGraphMetadata(BaseModel):
    title: str
    description: str
    url: str
    type: str = "article"
    site_name: str
    images: list[str]


class TwitterMetadata(BaseModel):
    card: Literal[
        "summary",
        "summary_large_image",
    ]
    title: str
    description: str
    images: list[str]


class SEOCheck(BaseModel):
    check_id: str
    status: SEOCheckStatus
    message: str
    weight: int


class SEOResult(BaseModel):
    seo_title: str
    meta_description: str
    slug: str
    canonical_url: str
    robots_meta: str | None
    open_graph: OpenGraphMetadata
    twitter: TwitterMetadata
    thumbnail_url: str | None = None
    schema_type: SchemaType
    json_ld: dict[str, Any]
    checks: list[SEOCheck]
    readiness_score: int
