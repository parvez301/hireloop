"""Star story CRUD helpers — Phase 1 model, Phase 2d API."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.star_story import StarStory
from hireloop.schemas.star_story import StarStoryCreate, StarStoryUpdate


class StarStoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(
        self, user_id: UUID, *, tags: list[str] | None = None
    ) -> list[StarStory]:
        stmt = (
            select(StarStory)
            .where(StarStory.user_id == user_id)
            .order_by(StarStory.created_at.desc())
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        if tags:
            rows = [r for r in rows if r.tags and any(t in r.tags for t in tags)]
        return rows

    async def get(self, user_id: UUID, story_id: UUID) -> StarStory | None:
        stmt = select(StarStory).where(
            StarStory.id == story_id,
            StarStory.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, user_id: UUID, payload: StarStoryCreate) -> StarStory:
        row = StarStory(
            user_id=user_id,
            title=payload.title,
            situation=payload.situation,
            task=payload.task,
            action=payload.action,
            result=payload.result,
            reflection=payload.reflection,
            tags=payload.tags,
            source="user_created",
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(
        self, user_id: UUID, story_id: UUID, payload: StarStoryUpdate
    ) -> StarStory | None:
        row = await self.get(user_id, story_id)
        if row is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(row, k, v)
        await self.session.flush()
        return row

    async def delete(self, user_id: UUID, story_id: UUID) -> bool:
        row = await self.get(user_id, story_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True
