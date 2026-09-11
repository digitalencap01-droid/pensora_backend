from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repository import content_repository
from app.db.webflow_repository import webflow_repository
from app.schemas.article import ArticleResult
from app.schemas.seo import SEOResult
from app.schemas.webflow import (
    WebflowCollection,
    WebflowCollectionsResult,
    WebflowConnectRequest,
    WebflowFieldOption,
    WebflowFieldsResult,
    WebflowPublishResult,
    WebflowSite,
    WebflowSitesResult,
    WebflowStatus,
)


API_BASE = "https://api.webflow.com/v2"


class WebflowNotConfigured(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            detail=(
                "Webflow publishing isn't configured on this "
                "server yet — set WEBFLOW_TOKEN."
            ),
        )


class WebflowNotConnected(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            detail=(
                "Connect a Webflow site and collection first."
            ),
        )


class WebflowItemNotFound(Exception):
    """Raised when Webflow 404s on an item we have an ID for — it
    was deleted directly in Webflow, out from under our stored
    project.webflow_item_id."""


class WebflowService:
    def _require_token(self) -> str:
        if not settings.webflow_token:
            raise WebflowNotConfigured()

        return settings.webflow_token.get_secret_value()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._require_token()}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        treat_404_as_missing: bool = False,
    ) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(
                method,
                f"{API_BASE}{path}",
                headers=self._headers(),
                json=json,
            )

        if treat_404_as_missing and response.status_code == 404:
            raise WebflowItemNotFound()

        if response.status_code >= 300:
            raise HTTPException(
                status_code=502,
                detail=f"Webflow API error: {response.text}",
            )

        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    # ---- discovery (used by the connect wizard) ----

    async def list_sites(self) -> WebflowSitesResult:
        data = await self._request("GET", "/sites")

        return WebflowSitesResult(
            sites=[
                WebflowSite(
                    id=site["id"],
                    display_name=site.get(
                        "displayName", site["id"]
                    ),
                    short_name=site.get("shortName"),
                )
                for site in data.get("sites", [])
            ]
        )

    async def list_collections(
        self,
        site_id: str,
    ) -> WebflowCollectionsResult:
        data = await self._request(
            "GET", f"/sites/{site_id}/collections"
        )

        return WebflowCollectionsResult(
            collections=[
                WebflowCollection(
                    id=collection["id"],
                    display_name=collection.get(
                        "displayName", collection["id"]
                    ),
                    slug=collection.get("slug", ""),
                )
                for collection in data.get("collections", [])
            ]
        )

    async def list_fields(
        self,
        collection_id: str,
    ) -> WebflowFieldsResult:
        data = await self._request(
            "GET", f"/collections/{collection_id}"
        )

        return WebflowFieldsResult(
            fields=[
                WebflowFieldOption(
                    slug=field["slug"],
                    display_name=field.get(
                        "displayName", field["slug"]
                    ),
                    type=field.get("type", ""),
                )
                for field in data.get("fields", [])
            ]
        )

    # ---- config (single global connection) ----

    async def get_status(
        self,
        session: AsyncSession,
    ) -> WebflowStatus:
        config = await webflow_repository.get_config(session)

        if config is None:
            return WebflowStatus(connected=False)

        return WebflowStatus(
            connected=True,
            site_id=config.site_id,
            site_name=config.site_name,
            collection_id=config.collection_id,
            collection_name=config.collection_name,
            title_field=config.title_field,
            slug_field=config.slug_field,
            body_field=config.body_field,
            summary_field=config.summary_field,
            main_image_field=config.main_image_field,
            thumbnail_field=config.thumbnail_field,
        )

    async def connect(
        self,
        session: AsyncSession,
        request: WebflowConnectRequest,
    ) -> WebflowStatus:
        self._require_token()

        await webflow_repository.upsert_config(
            session=session,
            site_id=request.site_id,
            site_name=request.site_name,
            collection_id=request.collection_id,
            collection_name=request.collection_name,
            title_field=request.title_field,
            slug_field=request.slug_field,
            body_field=request.body_field,
            summary_field=request.summary_field,
            main_image_field=request.main_image_field,
            thumbnail_field=request.thumbnail_field,
        )

        return await self.get_status(session)

    async def disconnect(
        self,
        session: AsyncSession,
    ) -> None:
        await webflow_repository.delete_config(session)

    # ---- publish ----

    async def _require_config(self, session: AsyncSession):
        config = await webflow_repository.get_config(session)

        if config is None:
            raise WebflowNotConnected()

        return config

    async def _require_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ):
        project = await content_repository.get_project(
            session, project_id
        )

        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found.",
            )

        return project

    async def _load_publishable_content(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> tuple[ArticleResult, SEOResult, str]:
        article_record = await content_repository.get_article_by_project(
            session, project_id
        )
        seo_record = await content_repository.get_latest_seo(
            session, project_id
        )
        file_record = await content_repository.get_latest_generated_file(
            session, project_id
        )

        if article_record is None or seo_record is None or file_record is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "This project hasn't finished generating yet — "
                    "there's no article/SEO/HTML to publish."
                ),
            )

        version_record = await content_repository.get_current_article_version(
            session, article_record
        )

        if version_record is None:
            raise HTTPException(
                status_code=400,
                detail="Article content is missing.",
            )

        article = ArticleResult.model_validate(version_record.payload)
        seo = SEOResult.model_validate(seo_record.payload)

        return article, seo, file_record.article_html

    def _build_field_data(
        self,
        config,
        article: ArticleResult,
        seo: SEOResult,
        article_html: str,
    ) -> dict:
        field_data = {
            config.title_field: article.title,
            config.slug_field: seo.slug,
            config.body_field: article_html,
            config.summary_field: seo.meta_description,
        }

        # Webflow's Image field expects {"url": ...} rather than a
        # bare string when writing through the API — it fetches and
        # rehosts whatever public URL is given.
        if config.main_image_field and seo.open_graph.images:
            field_data[config.main_image_field] = {
                "url": seo.open_graph.images[0]
            }

        if config.thumbnail_field and seo.thumbnail_url:
            field_data[config.thumbnail_field] = {
                "url": seo.thumbnail_url
            }

        return field_data

    def _dashboard_url(self, site_id: str) -> str:
        return f"https://webflow.com/dashboard/sites/{site_id}/cms"

    async def publish_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> WebflowPublishResult:
        self._require_token()
        config = await self._require_config(session)
        project = await self._require_project(session, project_id)

        article, seo, article_html = await self._load_publishable_content(
            session, project_id
        )
        field_data = self._build_field_data(
            config, article, seo, article_html
        )

        item_id: str | None = None
        status: str | None = None

        if project.webflow_item_id:
            # Already has a Webflow item — update it in place rather
            # than creating a duplicate. Keep whatever draft/live
            # state it already has; go_live() is the only thing that
            # flips it live.
            is_draft = project.webflow_publish_status != "live"
            try:
                await self._request(
                    "PATCH",
                    f"/collections/{config.collection_id}/items/{project.webflow_item_id}",
                    json={"isDraft": is_draft, "fieldData": field_data},
                    treat_404_as_missing=True,
                )
                item_id = project.webflow_item_id
                status = project.webflow_publish_status or "draft"
            except WebflowItemNotFound:
                # Deleted directly in Webflow — fall through and
                # create a fresh item instead of failing outright.
                pass

        if item_id is None:
            data = await self._request(
                "POST",
                f"/collections/{config.collection_id}/items",
                json={"isDraft": True, "fieldData": field_data},
            )
            item_id = data["id"]
            status = "draft"

        await webflow_repository.set_publish_state(
            session=session,
            project_id=project_id,
            item_id=item_id,
            status=status,
        )

        return WebflowPublishResult(
            item_id=item_id,
            status=status,
            dashboard_url=self._dashboard_url(config.site_id),
        )

    async def go_live(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> WebflowPublishResult:
        self._require_token()
        config = await self._require_config(session)
        project = await self._require_project(session, project_id)

        if not project.webflow_item_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Publish this article to Webflow as a draft "
                    "first."
                ),
            )

        # Re-send fieldData here too (not just isDraft) — a draft
        # created before a required field (e.g. thumbnail_field) was
        # mapped would otherwise still carry a null value for it, and
        # Webflow rejects going live with that null still in place.
        article, seo, article_html = await self._load_publishable_content(
            session, project_id
        )
        field_data = self._build_field_data(
            config, article, seo, article_html
        )

        try:
            await self._request(
                "PATCH",
                f"/collections/{config.collection_id}/items/{project.webflow_item_id}",
                json={"isDraft": False, "fieldData": field_data},
                treat_404_as_missing=True,
            )
        except WebflowItemNotFound as exc:
            await webflow_repository.clear_publish_state(
                session=session, project_id=project_id
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "That Webflow item was deleted directly in "
                    "Webflow — publish a new draft first."
                ),
            ) from exc

        await self._request(
            "POST",
            f"/collections/{config.collection_id}/items/publish",
            json={"itemIds": [project.webflow_item_id]},
        )

        await webflow_repository.set_publish_state(
            session=session,
            project_id=project_id,
            item_id=project.webflow_item_id,
            status="live",
        )

        return WebflowPublishResult(
            item_id=project.webflow_item_id,
            status="live",
            dashboard_url=self._dashboard_url(config.site_id),
        )


webflow_service = WebflowService()
