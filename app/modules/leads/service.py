from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.leads import Lead, LeadActivity
from app.modules.leads.repository import LeadRepository
from app.modules.leads.schemas import LeadCreate, LeadUpdate


class LeadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LeadRepository(session)

    async def create_lead(self, workspace_id: UUID, data: LeadCreate) -> Lead:
        lead = Lead(
            workspace_id=workspace_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            company_name=data.company_name,
            job_title=data.job_title,
            status=data.status,
            source=data.source,
            lead_score=data.lead_score,
            tags=data.tags,
            custom_fields_json=data.custom_fields_json,
            is_subscribed_email=data.is_subscribed_email,
            is_subscribed_whatsapp=data.is_subscribed_whatsapp,
            is_subscribed_sms=data.is_subscribed_sms,
        )
        created = await self.repo.create(lead)

        activity = LeadActivity(
            workspace_id=workspace_id,
            lead_id=created.id,
            activity_type="created",
            title="Lead Created",
            description="Manually created lead.",
        )
        self.session.add(activity)
        await self.session.commit()
        return created

    async def get_lead(self, workspace_id: UUID, lead_id: UUID) -> Lead | None:
        return await self.repo.get_by_id(workspace_id, lead_id)

    async def list_leads(
        self,
        workspace_id: UUID,
        search: str | None = None,
        status: str | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Lead], int]:
        return await self.repo.list_leads(
            workspace_id=workspace_id,
            search=search,
            status=status,
            source=source,
            page=page,
            page_size=page_size,
        )

    async def update_lead(self, workspace_id: UUID, lead_id: UUID, data: LeadUpdate) -> Lead | None:
        lead = await self.repo.get_by_id(workspace_id, lead_id)
        if not lead:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(lead, key, val)

        updated = await self.repo.update(lead)

        activity = LeadActivity(
            workspace_id=workspace_id,
            lead_id=lead.id,
            activity_type="updated",
            title="Lead Updated",
            description="Lead attributes updated.",
        )
        self.session.add(activity)
        await self.session.commit()
        return updated

    async def delete_lead(self, workspace_id: UUID, lead_id: UUID) -> bool:
        lead = await self.repo.get_by_id(workspace_id, lead_id)
        if not lead:
            return False
        await self.repo.delete(lead)
        await self.session.commit()
        return True
