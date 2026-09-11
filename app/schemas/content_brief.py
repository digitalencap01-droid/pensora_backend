from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.keywords import KeywordResult
from app.schemas.research import ResearchResult


ArticleType = Literal[
    "blog",
    "guide",
    "news",
    "tutorial",
    "comparison",
    "listicle",
    "thought_leadership",
    "case_study",
]


ToneType = Literal[
    "professional",
    "conversational",
    "technical",
    "educational",
    "authoritative",
]


class ContentBriefRequest(BaseModel):
    research: ResearchResult
    keywords: KeywordResult
    article_type: ArticleType = "blog"
    tone: ToneType = "professional"
    target_audience: str | None = Field(
        default=None,
        max_length=500,
    )
    target_word_count: int = Field(
        default=2000,
        ge=600,
        le=6000,
    )
    brand_name: str | None = Field(
        default=None,
        max_length=200,
    )
    call_to_action: str | None = Field(
        default=None,
        max_length=500,
    )


class OutlineSubsection(BaseModel):
    heading: str
    purpose: str
    target_keywords: list[str]
    questions_answered: list[str]
    evidence_urls: list[str]
    key_points: list[str]


class OutlineSection(BaseModel):
    section_id: str
    heading: str
    purpose: str
    target_keywords: list[str]
    semantic_terms: list[str]
    questions_answered: list[str]
    evidence_urls: list[str]
    key_points: list[str]
    subsections: list[OutlineSubsection]
    target_word_count: int


class ImageOpportunity(BaseModel):
    section_id: str
    image_type: Literal[
        "illustration",
        "diagram",
        "chart",
        "screenshot",
        "comparison",
        "infographic",
        "photo",
    ]
    purpose: str
    suggested_subject: str


class InternalLinkOpportunity(BaseModel):
    topic: str
    suggested_anchor_context: str
    target_section_id: str


class ContentBriefAI(BaseModel):
    content_angle: str
    unique_value_proposition: str
    target_reader: str
    reader_problem: str
    reader_outcome: str
    recommended_title: str
    alternative_titles: list[str]
    h1: str
    introduction_strategy: str
    sections: list[OutlineSection]
    conclusion_strategy: str
    cta_strategy: str | None
    image_opportunities: list[ImageOpportunity]
    internal_link_opportunities: list[
        InternalLinkOpportunity
    ]
    important_warnings: list[str]


class ContentBriefResult(BaseModel):
    topic: str
    article_type: ArticleType
    tone: ToneType
    target_word_count: int
    primary_keyword: str
    search_intent: str
    content_angle: str
    unique_value_proposition: str
    target_reader: str
    reader_problem: str
    reader_outcome: str
    recommended_title: str
    alternative_titles: list[str]
    h1: str
    introduction_strategy: str
    sections: list[OutlineSection]
    conclusion_strategy: str
    cta_strategy: str | None
    image_opportunities: list[ImageOpportunity]
    internal_link_opportunities: list[
        InternalLinkOpportunity
    ]
    important_warnings: list[str]
