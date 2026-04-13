"""ScanConfig CRUD service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.scan_config import ScanConfig
from hireloop.schemas.scan_config import ScanConfigCreate, ScanConfigUpdate


class ScanConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[ScanConfig]:
        stmt = (
            select(ScanConfig)
            .where(ScanConfig.user_id == user_id)
            .order_by(ScanConfig.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, user_id: UUID, config_id: UUID) -> ScanConfig | None:
        stmt = select(ScanConfig).where(
            ScanConfig.id == config_id,
            ScanConfig.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, user_id: UUID, payload: ScanConfigCreate) -> ScanConfig:
        config = ScanConfig(
            user_id=user_id,
            name=payload.name,
            companies=[c.model_dump() for c in payload.companies],
            keywords=payload.keywords,
            exclude_keywords=payload.exclude_keywords,
            schedule=payload.schedule,
            is_active=True,
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def update(
        self, user_id: UUID, config_id: UUID, payload: ScanConfigUpdate
    ) -> ScanConfig | None:
        config = await self.get(user_id, config_id)
        if config is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "companies" in data and data["companies"] is not None:
            data["companies"] = [
                c.model_dump() if hasattr(c, "model_dump") else c for c in data["companies"]
            ]
        for k, v in data.items():
            setattr(config, k, v)
        await self.session.flush()
        return config

    async def delete(self, user_id: UUID, config_id: UUID) -> bool:
        config = await self.get(user_id, config_id)
        if config is None:
            return False
        await self.session.delete(config)
        await self.session.flush()
        return True
