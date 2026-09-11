from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentProject, WebflowConfig


# Single global config row — see the comment above WebflowConfig.
_SINGLETON_ID = 1


class WebflowRepository:
    async def get_config(
        self,
        session: AsyncSession,
    ) -> WebflowConfig | None:
        return await session.get(WebflowConfig, _SINGLETON_ID)

    async def upsert_config(
        self,
        session: AsyncSession,
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
    ) -> WebflowConfig:
        config = await self.get_config(session)

        if config is None:
            config = WebflowConfig(id=_SINGLETON_ID)
            session.add(config)

        config.site_id = site_id
        config.site_name = site_name
        config.collection_id = collection_id
        config.collection_name = collection_name
        config.title_field = title_field
        config.slug_field = slug_field
        config.body_field = body_field
        config.summary_field = summary_field
        config.main_image_field = main_image_field
        config.thumbnail_field = thumbnail_field

        await session.commit()
        await session.refresh(config)
        return config

    async def delete_config(
        self,
        session: AsyncSession,
    ) -> None:
        config = await self.get_config(session)

        if config is None:
            return

        await session.delete(config)
        await session.commit()

    async def set_publish_state(
        self,
        session: AsyncSession,
        project_id: UUID,
        item_id: str,
        status: str,
    ) -> None:
        project = await session.get(ContentProject, project_id)

        if project is None:
            raise ValueError("Content project not found.")

        project.webflow_item_id = item_id
        project.webflow_publish_status = status

        await session.commit()

    async def clear_publish_state(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> None:
        project = await session.get(ContentProject, project_id)

        if project is None:
            raise ValueError("Content project not found.")

        project.webflow_item_id = None
        project.webflow_publish_status = None

        await session.commit()


webflow_repository = WebflowRepository()
