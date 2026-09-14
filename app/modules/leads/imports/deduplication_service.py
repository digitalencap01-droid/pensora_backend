from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.leads import Lead


class DeduplicationService:
    @staticmethod
    async def find_existing_lead(
        session: AsyncSession,
        workspace_id: UUID,
        email: str | None,
        phone: str | None,
    ) -> Lead | None:
        if not email and not phone:
            return None

        conditions = []
        if email:
            conditions.append(func.lower(Lead.email) == email.lower())
        if phone:
            conditions.append(Lead.phone == phone)

        query = select(Lead).where(
            Lead.workspace_id == workspace_id,
            or_(*conditions)
        )
        result = await session.execute(query)
        return result.scalars().first()
