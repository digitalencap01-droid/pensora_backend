from pydantic import BaseModel, Field

from app.schemas.content_brief import (
    ContentBriefResult,
)
from app.schemas.research import ResearchResult


class ArticleRequest(BaseModel):
    research: ResearchResult
    brief: ContentBriefResult
    language: str = Field(
        default="English",
        min_length=2,
        max_length=50,
    )
    additional_instructions: str | None = Field(
        default=None,
        max_length=1500,
    )


class ArticleSource(BaseModel):
    source_id: str
    title: str | None = None
    url: str
    domain: str


class GeneratedArticleBlockAI(BaseModel):
    content_markdown: str
    summary: str


class ArticleSection(BaseModel):
    section_id: str
    heading: str
    content_markdown: str
    citation_ids: list[str]
    summary: str
    word_count: int
    image_urls: list[str] = []
    image_alts: list[str] = []


class ArticleBlock(BaseModel):
    content_markdown: str
    citation_ids: list[str]
    word_count: int


class ArticleResult(BaseModel):
    topic: str
    title: str
    h1: str
    language: str
    introduction: ArticleBlock
    sections: list[ArticleSection]
    conclusion: ArticleBlock
    sources: list[ArticleSource]
    total_word_count: int
    article_markdown: str
