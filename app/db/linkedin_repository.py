from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LinkedInConnection


# Single global connection row — see the comment above LinkedInConnection.
_SINGLETON_ID = 1


class LinkedInRepository:
    async def get_connection(
        self,
        session: AsyncSession,
    ) -> LinkedInConnection | None:
        return await session.get(LinkedInConnection, _SINGLETON_ID)

    async def upsert_connection(
        self,
        session: AsyncSession,
        linkedin_member_id: str,
        linkedin_name: str | None,
        linkedin_email: str | None,
        access_token_encrypted: str,
        refresh_token_encrypted: str | None,
        scope: str,
        token_expires_at: datetime,
    ) -> LinkedInConnection:
        connection = await self.get_connection(session)

        if connection is None:
            connection = LinkedInConnection(id=_SINGLETON_ID)
            session.add(connection)

        connection.linkedin_member_id = linkedin_member_id
        connection.linkedin_name = linkedin_name
        connection.linkedin_email = linkedin_email
        connection.access_token_encrypted = access_token_encrypted
        connection.refresh_token_encrypted = refresh_token_encrypted
        connection.scope = scope
        connection.token_expires_at = token_expires_at

        await session.commit()
        await session.refresh(connection)
        return connection

    async def delete_connection(
        self,
        session: AsyncSession,
    ) -> None:
        connection = await self.get_connection(session)

        if connection is None:
            return

        await session.delete(connection)
        await session.commit()


linkedin_repository = LinkedInRepository()
