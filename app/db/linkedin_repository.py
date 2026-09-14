from datetime import datetime
from types import SimpleNamespace

from app.db.supabase_rest import row, supabase_rest


# Single global connection row — see the comment above LinkedInConnection.
_SINGLETON_ID = 1


class LinkedInRepository:
    async def get_connection(
        self,
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "linkedin_connections",
            params={"id": f"eq.{_SINGLETON_ID}"},
        )
        return row(data) if data else None

    async def upsert_connection(
        self,
        linkedin_member_id: str,
        linkedin_name: str | None,
        linkedin_email: str | None,
        access_token_encrypted: str,
        refresh_token_encrypted: str | None,
        scope: str,
        token_expires_at: datetime,
    ) -> SimpleNamespace:
        data = {
            "id": _SINGLETON_ID,
            "linkedin_member_id": linkedin_member_id,
            "linkedin_name": linkedin_name,
            "linkedin_email": linkedin_email,
            "access_token_encrypted": (
                access_token_encrypted
            ),
            "refresh_token_encrypted": (
                refresh_token_encrypted
            ),
            "scope": scope,
            "token_expires_at": (
                token_expires_at.isoformat()
            ),
        }

        result = await supabase_rest.insert_one(
            "linkedin_connections",
            data,
            on_conflict="id",
        )
        return row(result)

    async def delete_connection(self) -> None:
        await supabase_rest.delete(
            "linkedin_connections",
            params={"id": f"eq.{_SINGLETON_ID}"},
        )


linkedin_repository = LinkedInRepository()
