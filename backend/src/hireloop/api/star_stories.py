"""Star stories API — non-paywalled CRUD."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.api.errors import AppError
from hireloop.schemas.star_story import (
    StarStoryCreate,
    StarStoryOut,
    StarStoryUpdate,
)
from hireloop.services.star_story import StarStoryService

router = APIRouter(prefix="/star-stories", tags=["star-stories"])


@router.get("")
async def list_star_stories(
    user: CurrentDbUser,
    session: DbSession,
    tags: str | None = Query(default=None, description="Comma-separated tag filter"),
) -> dict[str, Any]:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    rows = await StarStoryService(session).list_for_user(user.id, tags=tag_list)
    return {"data": [StarStoryOut.model_validate(r).model_dump(mode="json") for r in rows]}


@router.post("", status_code=201)
async def create_star_story(
    payload: StarStoryCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await StarStoryService(session).create(user.id, payload)
    await session.commit()
    return {"data": StarStoryOut.model_validate(row).model_dump(mode="json")}


@router.get("/{story_id}")
async def get_star_story(
    story_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await StarStoryService(session).get(user.id, story_id)
    if row is None:
        raise AppError(404, "STAR_STORY_NOT_FOUND", "Star story not found")
    return {"data": StarStoryOut.model_validate(row).model_dump(mode="json")}


@router.put("/{story_id}")
async def update_star_story(
    story_id: UUID,
    payload: StarStoryUpdate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await StarStoryService(session).update(user.id, story_id, payload)
    if row is None:
        raise AppError(404, "STAR_STORY_NOT_FOUND", "Star story not found")
    await session.commit()
    return {"data": StarStoryOut.model_validate(row).model_dump(mode="json")}


@router.delete("/{story_id}", status_code=204)
async def delete_star_story(
    story_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> None:
    ok = await StarStoryService(session).delete(user.id, story_id)
    if not ok:
        raise AppError(404, "STAR_STORY_NOT_FOUND", "Star story not found")
    await session.commit()
