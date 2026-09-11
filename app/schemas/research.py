from typing import Literal

from pydantic import BaseModel, Field, field_validator


Freshness = Literal[
    "24h",
    "7d",
    "30d",
    "90d",
    "1y",
    "any",
]


class ResearchRequest(BaseModel):
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

    freshness: Freshness = "30d"

    max_queries: int = Field(
        default=4,
        ge=2,
        le=6,
    )

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.upper().strip()


class ResearchQueryPlan(BaseModel):
    search_intent: str
    queries: list[str]
    questions_to_answer: list[str]


class ResearchSource(BaseModel):
    title: str | None = None
    url: str
    domain: str


class ResearchFact(BaseModel):
    claim: str
    source_urls: list[str]


class ResearchSynthesis(BaseModel):
    search_intent: str
    summary: str
    questions_to_answer: list[str]
    key_facts: list[ResearchFact]
    statistics: list[ResearchFact]
    recent_developments: list[ResearchFact]
    important_entities: list[str]
    controversies_or_uncertainties: list[str]
    content_gaps: list[str]
    article_angles: list[str]


class ResearchResult(BaseModel):
    topic: str
    search_intent: str
    summary: str
    queries_used: list[str]
    questions_to_answer: list[str]
    key_facts: list[ResearchFact]
    statistics: list[ResearchFact]
    recent_developments: list[ResearchFact]
    important_entities: list[str]
    controversies_or_uncertainties: list[str]
    content_gaps: list[str]
    article_angles: list[str]
    sources: list[ResearchSource]
