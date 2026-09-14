from types import SimpleNamespace
from uuid import UUID

from app.db.supabase_rest import row, supabase_rest


# Single global config row — see the comment above WebflowConfig.
_SINGLETON_ID = 1


class WebflowRepository:
    async def get_config(
        self,
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "webflow_config",
            params={"id": f"eq.{_SINGLETON_ID}"},
        )
        return row(data) if data else None

    async def upsert_config(
        self,
        site_id: str,
        site_name: str,
        collection_id: str,
        collection_name: str,
        title_field: str,
        slug_field: str,
        body_field: str,
        summary_field: str,
        main_image_field: str | None,
        thumbnail_field: str | None,
    ) -> SimpleNamespace:
        data = {
            "id": _SINGLETON_ID,
            "site_id": site_id,
            "site_name": site_name,
            "collection_id": collection_id,
            "collection_name": collection_name,
            "title_field": title_field,
            "slug_field": slug_field,
            "body_field": body_field,
            "summary_field": summary_field,
            "main_image_field": main_image_field,
            "thumbnail_field": thumbnail_field,
        }

        result = await supabase_rest.insert_one(
            "webflow_config",
            data,
            on_conflict="id",
        )
        return row(result)

    async def delete_config(self) -> None:
        await supabase_rest.delete(
            "webflow_config",
            params={"id": f"eq.{_SINGLETON_ID}"},
        )

    async def set_publish_state(
        self,
        project_id: UUID,
        item_id: str,
        status: str,
    ) -> None:
        result = await supabase_rest.update(
            "content_projects",
            {
                "webflow_item_id": item_id,
                "webflow_publish_status": status,
            },
            params={"id": f"eq.{project_id}"},
        )

        if not result:
            raise ValueError(
                "Content project not found."
            )

    async def clear_publish_state(
        self,
        project_id: UUID,
    ) -> None:
        result = await supabase_rest.update(
            "content_projects",
            {
                "webflow_item_id": None,
                "webflow_publish_status": None,
            },
            params={"id": f"eq.{project_id}"},
        )

        if not result:
            raise ValueError(
                "Content project not found."
            )


webflow_repository = WebflowRepository()
