from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, model_validator


LinkedInContentType = Literal["post", "article"]


class LinkedInStatus(BaseModel):
    connected: bool
    linkedin_name: str | None = None


class LinkedInConnectResult(BaseModel):
    authorize_url: str


class GeneratedLinkedInContentAI(BaseModel):
    text: str


class LinkedInGenerateRequest(BaseModel):
    content_type: LinkedInContentType
    topic: str = Field(..., min_length=1, max_length=300)
    tone: str | None = Field(default=None, max_length=100)
    use_web_search: bool = False
    document_id: UUID | None = None
    image_batch_id: UUID | None = None

    @model_validator(mode="after")
    def validate_grounding_selection(
        self,
    ) -> "LinkedInGenerateRequest":
        if self.document_id and self.image_batch_id:
            raise ValueError(
                "document_id and image_batch_id are mutually exclusive."
            )
        return self


class LinkedInGenerateResult(BaseModel):
    content_type: LinkedInContentType
    text: str
    hashtags: list[str] = Field(default_factory=list)


class LinkedInPostPublishRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=12000)


class SuggestedHashtagsAI(BaseModel):
    hashtags: list[str]


class LinkedInHashtagSuggestRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=300)
    content_type: LinkedInContentType
    draft_text: str | None = Field(default=None, max_length=3000)


class LinkedInHashtagSuggestResult(BaseModel):
    hashtags: list[str]


class LinkedInPublishRequest(BaseModel):
    article_title: str = Field(..., min_length=1, max_length=500)
    article_summary: str = Field(default="", max_length=2000)
    article_url: HttpUrl
    # No thumbnail field: LinkedIn's article share doesn't accept an
    # explicit image — it scrapes the og:image from article_url, which
    # this app's SEO service already sets (see SEOResult.open_graph).
    commentary: str | None = Field(default=None, max_length=12000)


class LinkedInPublishResult(BaseModel):
    post_urn: str
    post_url: str | None = None
