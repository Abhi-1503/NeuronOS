import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import Automation, AutomationRun


class AutomationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, automation: Automation) -> None:
        self._session.add(automation)

    async def get_by_id(self, automation_id: uuid.UUID) -> Automation | None:
        result = await self._session.execute(
            select(Automation).where(
                Automation.id == automation_id, Automation.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_active_org_automations(self) -> list[Automation]:
        result = await self._session.execute(
            select(Automation).where(
                Automation.deleted_at.is_(None), Automation.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Automation]:
        result = await self._session.execute(
            select(Automation).where(Automation.deleted_at.is_(None)).order_by(Automation.created_at)
        )
        return list(result.scalars().all())

    def add_run(self, run: AutomationRun) -> None:
        self._session.add(run)

    async def get_run_by_idempotency_key(
        self, automation_id: uuid.UUID, idempotency_key: str
    ) -> AutomationRun | None:
        result = await self._session.execute(
            select(AutomationRun).where(
                AutomationRun.automation_id == automation_id,
                AutomationRun.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_runs(
        self, automation_id: uuid.UUID, *, status: str | None = None, limit: int = 25
    ) -> list[AutomationRun]:
        query = select(AutomationRun).where(AutomationRun.automation_id == automation_id)
        if status:
            query = query.where(AutomationRun.status == status)
        query = query.order_by(AutomationRun.triggered_at.desc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())
