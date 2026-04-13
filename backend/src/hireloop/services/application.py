"""Application service — CRUD scoped by user_id."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.application import Application
from hireloop.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[Application]:
        stmt = select(Application).where(Application.user_id == user_id)
        if status:
            stmt = stmt.where(Application.status == status)
        stmt = stmt.order_by(Application.updated_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, user_id: UUID, app_id: UUID) -> Application | None:
        stmt = select(Application).where(Application.id == app_id, Application.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, user_id: UUID, payload: ApplicationCreate) -> Application | None:
        row = Application(
            user_id=user_id,
            job_id=payload.job_id,
            status=payload.status,
            evaluation_id=payload.evaluation_id,
            cv_output_id=payload.cv_output_id,
            notes=payload.notes,
            applied_at=datetime.now(UTC) if payload.status == "applied" else None,
        )
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            return None
        return row

    async def update(
        self, user_id: UUID, app_id: UUID, payload: ApplicationUpdate
    ) -> Application | None:
        app = await self.get(user_id, app_id)
        if app is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "status" in data and data["status"] == "applied" and app.applied_at is None:
            app.applied_at = datetime.now(UTC)
        for k, v in data.items():
            setattr(app, k, v)
        app.updated_at = datetime.now(UTC)
        await self.session.flush()
        return app

    async def delete(self, user_id: UUID, app_id: UUID) -> bool:
        app = await self.get(user_id, app_id)
        if app is None:
            return False
        await self.session.delete(app)
        await self.session.flush()
        return True
