from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.article import ArticleResult
from app.schemas.seo import SEOResult


class HTMLRenderRequest(BaseModel):
    article: ArticleResult
    seo: SEOResult
    language_code: str = Field(
        default="en",
        min_length=2,
        max_length=15,
    )
    text_direction: Literal[
        "ltr",
        "rtl",
    ] = "ltr"
    featured_image_alt: str | None = Field(
        default=None,
        max_length=500,
    )
    include_sources: bool = True
    save_file: bool = True


class HTMLRenderResult(BaseModel):
    filename: str
    full_html: str
    article_html: str
    saved: bool
    relative_path: str | None = None
