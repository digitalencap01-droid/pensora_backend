from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID

import httpx

from app.core.config import settings


def _json_safe(value: Any) -> Any:
    """Recursively converts UUIDs (and similar) into strings so the
    payload can be sent as JSON to PostgREST."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def row(data: dict) -> SimpleNamespace:
    """Wraps a PostgREST JSON row as an attribute-accessible object,
    so the rest of the app can keep using `record.id` / `record.payload`
    instead of `record["id"]` — same shape callers already expect from
    the old SQLAlchemy ORM rows."""
    return SimpleNamespace(**data)


class SupabaseRestError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"PostgREST error {status_code}: {detail}")


class SupabaseRestClient:
    """Thin wrapper over Supabase's auto-generated PostgREST API
    (`{SUPABASE_URL}/rest/v1`), used instead of a direct Postgres
    connection — see README.md for why.

    Always authenticates as the service_role key, which bypasses RLS
    the same way the app's previous direct DB connection did (this
    app runs without per-request authentication).
    """

    def __init__(self) -> None:
        self.base_url = (
            f"{settings.supabase_url.rstrip('/')}/rest/v1"
        )

    def _headers(
        self,
        extra: dict | None = None,
        *,
        write: bool = False,
    ) -> dict:
        key = settings.supabase_service_role_key or ""
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        # Targets a non-default Postgres schema (e.g. "ai_blog")
        # when PGRST_DB_SCHEMAS on the server exposes more than just
        # "public" — see README.md. PostgREST uses different headers
        # for reads vs. writes.
        if settings.db_schema and settings.db_schema != "public":
            header_name = (
                "Content-Profile" if write else "Accept-Profile"
            )
            headers[header_name] = settings.db_schema

        if extra:
            headers.update(extra)
        return headers

    async def select(
        self,
        table: str,
        *,
        params: dict | None = None,
    ) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/{table}",
                params=params or {},
                headers=self._headers(),
            )
        self._raise_for_status(response)
        return response.json()

    async def select_one(
        self,
        table: str,
        *,
        params: dict | None = None,
    ) -> dict | None:
        merged = {**(params or {}), "limit": "1"}
        rows = await self.select(table, params=merged)
        return rows[0] if rows else None

    async def insert(
        self,
        table: str,
        data: dict | list[dict],
        *,
        on_conflict: str | None = None,
    ) -> list[dict]:
        params = {}
        prefer = "return=representation"
        if on_conflict:
            params["on_conflict"] = on_conflict
            prefer += ",resolution=merge-duplicates"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/{table}",
                params=params,
                json=_json_safe(data),
                headers=self._headers(
                    {"Prefer": prefer}, write=True
                ),
            )
        self._raise_for_status(response)
        return response.json()

    async def insert_one(
        self,
        table: str,
        data: dict,
        *,
        on_conflict: str | None = None,
    ) -> dict:
        result = await self.insert(
            table, data, on_conflict=on_conflict
        )
        return result[0]

    async def update(
        self,
        table: str,
        data: dict,
        *,
        params: dict,
    ) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"{self.base_url}/{table}",
                params=params,
                json=_json_safe(data),
                headers=self._headers(
                    {"Prefer": "return=representation"},
                    write=True,
                ),
            )
        self._raise_for_status(response)
        return response.json()

    async def delete(
        self,
        table: str,
        *,
        params: dict,
    ) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.base_url}/{table}",
                params=params,
                headers=self._headers(write=True),
            )
        self._raise_for_status(response)

    async def count(
        self,
        table: str,
        *,
        params: dict | None = None,
    ) -> int:
        merged = {
            **(params or {}),
            "select": "id",
            "limit": "0",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/{table}",
                params=merged,
                headers=self._headers(
                    {"Prefer": "count=exact"}
                ),
            )
        self._raise_for_status(response)
        content_range = response.headers.get(
            "content-range", "*/0"
        )
        total = content_range.split("/")[-1]
        return int(total) if total.isdigit() else 0

    def _raise_for_status(
        self, response: httpx.Response
    ) -> None:
        if response.status_code >= 400:
            raise SupabaseRestError(
                response.status_code, response.text
            )


supabase_rest = SupabaseRestClient()
