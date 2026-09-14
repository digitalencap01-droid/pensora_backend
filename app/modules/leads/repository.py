from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.leads import Lead, LeadActivity, LeadImportJob


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, workspace_id: UUID, lead_id: UUID) -> Lead | None:
        result = await self.session.execute(
            select(Lead).where(
                Lead.workspace_id == workspace_id,
                Lead.id == lead_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, workspace_id: UUID, email: str) -> Lead | None:
        result = await self.session.execute(
            select(Lead).where(
                Lead.workspace_id == workspace_id,
                func.lower(Lead.email) == email.lower()
            )
        )
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        workspace_id: UUID | str,
        search: str | None = None,
        status: str | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Lead], int]:
        query = select(Lead).where(Lead.workspace_id == str(workspace_id))

        if status:
            query = query.where(Lead.status == status)
        if source:
            query = query.where(Lead.source == source)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Lead.first_name.ilike(search_pattern),
                    Lead.last_name.ilike(search_pattern),
                    Lead.full_name.ilike(search_pattern),
                    Lead.email.ilike(search_pattern),
                    Lead.phone.ilike(search_pattern),
                    Lead.company_name.ilike(search_pattern),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(Lead.created_at.desc()).offset(offset).limit(page_size)
        items_result = await self.session.execute(query)
        items = list(items_result.scalars().all())

        return items, total

    async def create(self, lead: Lead) -> Lead:
        if lead.first_name or lead.last_name:
            lead.full_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def update(self, lead: Lead) -> Lead:
        if lead.first_name or lead.last_name:
            lead.full_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
        await self.session.flush()
        return lead

    async def delete(self, lead: Lead) -> None:
        await self.session.delete(lead)
        await self.session.flush()

    async def create_import_job(self, job: LeadImportJob) -> LeadImportJob:
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_import_job(self, workspace_id: UUID, job_id: UUID) -> LeadImportJob | None:
        result = await self.session.execute(
            select(LeadImportJob).where(
                LeadImportJob.workspace_id == workspace_id,
                LeadImportJob.id == job_id
            )
        )
        return result.scalar_one_or_none()
