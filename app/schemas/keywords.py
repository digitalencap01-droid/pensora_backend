from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.research import ResearchResult


SearchIntent = Literal[
    "informational",
    "commercial",
    "transactional",
    "navigational",
    "local",
    "mixed",
]


ReaderStage = Literal[
    "awareness",
    "consideration",
    "decision",
    "mixed",
]


ContentGoal = Literal[
    "organic_traffic",
    "education",
    "thought_leadership",
    "lead_generation",
    "product_discovery",
]


KeywordPlacement = Literal[
    "title",
    "h1",
    "introduction",
    "h2",
    "body",
    "image_alt",
    "internal_link_anchor",
]


class KeywordRequest(BaseModel):
    research: ResearchResult

    language: str = Field(
        default="English",
        min_length=2,
        max_length=50,
    )

    country_code: str = Field(
        default="IN",
        min_length=2,
        max_length=2,
    )

    target_audience: str | None = Field(
        default=None,
        max_length=300,
    )

    content_goal: ContentGoal = "organic_traffic"

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(
        cls,
        value: str,
    ) -> str:
        return value.strip().upper()


class KeywordItem(BaseModel):
    keyword: str
    intent: SearchIntent
    rationale: str
    recommended_placements: list[
        KeywordPlacement
    ]


class SearchIntentProfile(BaseModel):
    primary_intent: SearchIntent
    secondary_intents: list[SearchIntent]
    reader_goal: str
    reader_stage: ReaderStage
    expected_answers: list[str]
    recommended_content_format: str


class KeywordStrategyAI(BaseModel):
    search_intent: SearchIntentProfile
    primary_keyword: KeywordItem
    secondary_keywords: list[KeywordItem]
    semantic_terms: list[str]
    long_tail_keywords: list[KeywordItem]
    question_keywords: list[KeywordItem]
    must_cover_topics: list[str]
    title_directions: list[str]
    heading_terms: list[str]
    internal_link_topics: list[str]
    differentiation_opportunities: list[str]


class KeywordResult(BaseModel):
    topic: str
    search_intent: SearchIntentProfile
    primary_keyword: KeywordItem
    secondary_keywords: list[KeywordItem]
    semantic_terms: list[str]
    long_tail_keywords: list[KeywordItem]
    question_keywords: list[KeywordItem]
    must_cover_topics: list[str]
    title_directions: list[str]
    heading_terms: list[str]
    internal_link_topics: list[str]
    differentiation_opportunities: list[str]
    metrics_status: Literal[
        "not_connected"
    ] = "not_connected"
