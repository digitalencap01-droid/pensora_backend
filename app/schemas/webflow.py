from typing import Literal

from pydantic import BaseModel, Field


WebflowPublishState = Literal["draft", "live"]


class WebflowSite(BaseModel):
    id: str
    display_name: str
    short_name: str | None = None


class WebflowSitesResult(BaseModel):
    sites: list[WebflowSite]


class WebflowCollection(BaseModel):
    id: str
    display_name: str
    slug: str


class WebflowCollectionsResult(BaseModel):
    collections: list[WebflowCollection]


class WebflowFieldOption(BaseModel):
    slug: str
    display_name: str
    type: str


class WebflowFieldsResult(BaseModel):
    fields: list[WebflowFieldOption]


class WebflowConnectRequest(BaseModel):
    site_id: str = Field(..., min_length=1)
    site_name: str = Field(..., min_length=1, max_length=200)
    collection_id: str = Field(..., min_length=1)
    collection_name: str = Field(..., min_length=1, max_length=200)
    # Webflow CMS field slugs to write the article into — every
    # collection can name these differently, so they're picked during
    # setup rather than hardcoded (see spike.py for the defaults these
    # come from: name/slug/post-body/post-summary).
    title_field: str = Field(default="name", min_length=1, max_length=100)
    slug_field: str = Field(default="slug", min_length=1, max_length=100)
    body_field: str = Field(default="post-body", min_length=1, max_length=100)
    summary_field: str = Field(default="post-summary", min_length=1, max_length=100)
    # Optional image fields — only needed if the collection has them.
    # Webflow allows an image field to stay unset while an item is a
    # draft, but rejects going live if it's required and still null,
    # so both must be mapped up front if the collection requires them.
    main_image_field: str | None = Field(default=None, max_length=100)
    thumbnail_field: str | None = Field(default=None, max_length=100)


class WebflowStatus(BaseModel):
    connected: bool
    site_id: str | None = None
    site_name: str | None = None
    collection_id: str | None = None
    collection_name: str | None = None
    title_field: str | None = None
    slug_field: str | None = None
    body_field: str | None = None
    summary_field: str | None = None
    main_image_field: str | None = None
    thumbnail_field: str | None = None


class WebflowPublishResult(BaseModel):
    item_id: str
    status: WebflowPublishState
    dashboard_url: str | None = None
