from datetime import datetime
from uuid import UUID, uuid4
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.modules.leads.schemas import LeadCreate, LeadUpdate


class SupabaseLead(BaseModel):
    id: UUID
    workspace_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    status: str = "new"
    source: str = "manual"
    lead_score: int = 0
    tags: list[str] = []
    custom_fields_json: dict = {}
    is_subscribed_email: bool = True
    is_subscribed_whatsapp: bool = True
    is_subscribed_sms: bool = True
    created_at: datetime
    updated_at: datetime


class SupabaseLeadImportJob(BaseModel):
    id: UUID
    workspace_id: UUID
    filename: str
    file_size_bytes: int
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    duplicate_rows: int = 0
    status: str = "pending"
    field_mappings_json: dict = {}
    error_log_json: list = []
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class SupabaseLeadRepository:
    """Repository connecting directly to Supabase REST API (growth schema) via Service Role Key."""

    def __init__(self) -> None:
        self.base_url = settings.supabase_url.rstrip("/")
        self.key = settings.supabase_service_role_key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept-Profile": settings.db_schema or "growth",
            "Content-Profile": settings.db_schema or "growth",
        }

    def _map_from_supabase(self, item: dict) -> dict:
        return {
            "id": item.get("id"),
            "workspace_id": item.get("workspace_id") or "00000000-0000-0000-0000-000000000000",
            "first_name": item.get("first_name"),
            "last_name": item.get("last_name"),
            "full_name": item.get("full_name") or f"{item.get('first_name') or ''} {item.get('last_name') or ''}".strip(),
            "email": item.get("primary_email") or item.get("email"),
            "phone": item.get("primary_phone") or item.get("phone"),
            "company_name": item.get("company_name"),
            "job_title": item.get("job_title"),
            "status": item.get("lead_status") or item.get("status") or "new",
            "source": item.get("first_source_name") or item.get("source") or "manual",
            "lead_score": item.get("lead_score", 0),
            "tags": item.get("tags") or [],
            "custom_fields_json": item.get("custom_fields") or item.get("custom_fields_json") or {},
            "is_subscribed_email": item.get("is_subscribed_email", True),
            "is_subscribed_whatsapp": item.get("is_subscribed_whatsapp", True),
            "is_subscribed_sms": item.get("is_subscribed_sms", True),
            "created_at": item.get("created_at") or datetime.utcnow().isoformat(),
            "updated_at": item.get("updated_at") or datetime.utcnow().isoformat(),
        }

    def _map_to_supabase(self, data: dict) -> dict:
        sb_data = {}
        if "id" in data and data["id"]:
            sb_data["id"] = str(data["id"])
        else:
            sb_data["id"] = str(uuid4())

        sb_data["workspace_id"] = str(data.get("workspace_id") or "00000000-0000-0000-0000-000000000000")

        if "full_name" in data and data["full_name"]:
            sb_data["full_name"] = data["full_name"]
            if "first_name" not in data:
                parts = data["full_name"].strip().split(" ", 1)
                sb_data["first_name"] = parts[0]
                if len(parts) > 1:
                    sb_data["last_name"] = parts[1]
        if "first_name" in data and data["first_name"]:
            sb_data["first_name"] = data["first_name"]
        if "last_name" in data and data["last_name"]:
            sb_data["last_name"] = data["last_name"]
        if ("first_name" in data or "last_name" in data) and ("full_name" not in sb_data or not sb_data["full_name"]):
            sb_data["full_name"] = f"{data.get('first_name') or ''} {data.get('last_name') or ''}".strip()

        if "email" in data and data["email"]:
            sb_data["primary_email"] = data["email"]
        if "phone" in data and data["phone"]:
            sb_data["primary_phone"] = data["phone"]
        if "company_name" in data and data["company_name"]:
            sb_data["company_name"] = data["company_name"]
        if "job_title" in data and data["job_title"]:
            sb_data["job_title"] = data["job_title"]

        # Handle lead_status check constraint safely
        valid_statuses = {"new", "contacted", "qualified", "unqualified", "lost", "converted"}
        raw_status = str(data.get("status") or "new").lower().strip()
        if raw_status in valid_statuses:
            sb_data["lead_status"] = raw_status
        else:
            sb_data["lead_status"] = "new"

        if "source" in data and data["source"]:
            sb_data["first_source_name"] = data["source"]
        if "lead_score" in data and data["lead_score"] is not None:
            try:
                sb_data["lead_score"] = int(data["lead_score"])
            except (ValueError, TypeError):
                sb_data["lead_score"] = 0

        # Custom fields & tags (since 'tags' is not a column in leads table)
        custom = dict(data.get("custom_fields_json") or {})
        if "tags" in data and data["tags"]:
            if isinstance(data["tags"], list):
                custom["Tags"] = ", ".join(data["tags"])
            elif isinstance(data["tags"], str):
                custom["Tags"] = data["tags"]

        sb_data["custom_fields"] = custom
        return sb_data

    async def list_leads(
        self,
        workspace_id: UUID | str,
        search: str | None = None,
        status: str | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SupabaseLead], int]:
        params = {"select": "*"}
        if status:
            params["lead_status"] = f"eq.{status}"
        if search:
            search_str = search.strip()
            params["or"] = (
                f"(first_name.ilike.*{search_str}*,last_name.ilike.*{search_str}*,"
                f"full_name.ilike.*{search_str}*,primary_email.ilike.*{search_str}*,"
                f"company_name.ilike.*{search_str}*)"
            )

        offset = (page - 1) * page_size
        headers = {
            **self.headers,
            "Prefer": "count=exact",
            "Range": f"{offset}-{offset + page_size - 1}",
        }

        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get(
                f"{self.base_url}/rest/v1/leads",
                headers=headers,
                params=params,
                timeout=10.0,
            )

        if res.status_code not in (200, 206):
            return [], 0

        # Parse total count from Content-Range header (e.g. 0-9/25)
        content_range = res.headers.get("Content-Range", "")
        total = 0
        if "/" in content_range:
            total_part = content_range.split("/")[-1]
            if total_part.isdigit():
                total = int(total_part)

        raw_items = res.json()
        items = [SupabaseLead(**self._map_from_supabase(i)) for i in raw_items]
        if total == 0:
            total = len(items)

        return items, total

    async def get_by_id(self, workspace_id: UUID | str, lead_id: UUID | str) -> SupabaseLead | None:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get(
                f"{self.base_url}/rest/v1/leads",
                headers=self.headers,
                params={"id": f"eq.{lead_id}", "select": "*"},
                timeout=10.0,
            )
        if res.status_code == 200 and res.json():
            return SupabaseLead(**self._map_from_supabase(res.json()[0]))
        return None

    async def create(self, lead_data: dict) -> SupabaseLead:
        if "id" not in lead_data or not lead_data["id"]:
            lead_data["id"] = str(uuid4())
        if "workspace_id" not in lead_data or not lead_data["workspace_id"]:
            lead_data["workspace_id"] = "00000000-0000-0000-0000-000000000000"

        sb_payload = self._map_to_supabase(lead_data)
        headers = {**self.headers, "Prefer": "return=representation"}

        async with httpx.AsyncClient(verify=False) as client:
            res = await client.post(
                f"{self.base_url}/rest/v1/leads",
                headers=headers,
                json=sb_payload,
                timeout=10.0,
            )
        res.raise_for_status()
        created_item = res.json()[0]
        return SupabaseLead(**self._map_from_supabase(created_item))

    async def update(self, lead_id: UUID | str, update_data: dict) -> SupabaseLead | None:
        sb_payload = self._map_to_supabase(update_data)
        headers = {**self.headers, "Prefer": "return=representation"}

        async with httpx.AsyncClient(verify=False) as client:
            res = await client.patch(
                f"{self.base_url}/rest/v1/leads",
                headers=headers,
                params={"id": f"eq.{lead_id}"},
                json=sb_payload,
                timeout=10.0,
            )
        if res.status_code == 200 and res.json():
            return SupabaseLead(**self._map_from_supabase(res.json()[0]))
        return None

    async def delete(self, lead_id: UUID | str) -> bool:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.delete(
                f"{self.base_url}/rest/v1/leads",
                headers=self.headers,
                params={"id": f"eq.{lead_id}"},
                timeout=10.0,
            )
        return res.status_code in (200, 204)
