"""Conversations + messages API — CRUD, blocking send, and SSE replay."""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from hireloop.api.deps import DbSession, EntitledDbUser, RedisClient
from hireloop.config import get_settings
from hireloop.core.agent.runner import run_turn
from hireloop.models.conversation import Message
from hireloop.schemas.agent import SseEvent
from hireloop.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    MessageCreate,
    MessageOut,
)
from hireloop.services.conversation import ConversationService
from hireloop.services.rate_limit import RateLimiter

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _rate_limiter(redis: Redis) -> RateLimiter:
    settings = get_settings()
    cap = settings.agent_message_rate_limit_per_minute
    return RateLimiter(
        redis,
        capacity=cap,
        refill_per_second=cap / 60.0,
        bucket_name="msg",
    )


@router.post("")
async def create_conversation(
    payload: ConversationCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    service = ConversationService(session)
    row = await service.create(user.id, title=payload.title)
    await session.commit()
    return {"data": ConversationOut.model_validate(row).model_dump(mode="json")}


@router.get("")
async def list_conversations(
    user: EntitledDbUser,
    session: DbSession,
    limit: int = 20,
) -> dict[str, Any]:
    service = ConversationService(session)
    rows = await service.list_for_user(user.id, limit=limit)
    return {
        "data": [ConversationOut.model_validate(r).model_dump(mode="json") for r in rows],
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    service = ConversationService(session)
    conv = await service.get(user.id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await service.list_messages(conv.id, limit=50)
    detail = ConversationDetail(
        conversation=ConversationOut.model_validate(conv),
        messages=[MessageOut.model_validate(m) for m in messages],
    )
    return {"data": detail.model_dump(mode="json", by_alias=True)}


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    user: EntitledDbUser,
    session: DbSession,
) -> None:
    service = ConversationService(session)
    ok = await service.delete(user.id, conversation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await session.commit()


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    user: EntitledDbUser,
    session: DbSession,
    redis: RedisClient,
) -> dict[str, Any]:
    limiter = _rate_limiter(redis)
    await limiter.check(str(user.id))

    service = ConversationService(session)
    conv = await service.get(user.id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    placeholder = await service.create_placeholder_assistant_message(conv.id)

    assistant_row = await run_turn(
        session=session,
        user=user,
        conversation=conv,
        user_message_text=payload.content,
        assistant_message_id=placeholder.id,
        emit=None,
    )

    await service.auto_title_from_first_message(conv.id, payload.content)
    await service.touch(conv.id)
    await session.commit()

    meta = assistant_row.meta_ or {}
    return {
        "data": MessageOut.model_validate(assistant_row).model_dump(mode="json", by_alias=True),
        "meta": {
            "tokens_used": meta.get("tokens_used", 0),
            "cost_cents": meta.get("cost_cents", 0),
        },
    }


def _format_event(event: SseEvent) -> str:
    return f"event: {event.event_type}\ndata: {_json.dumps(event.data)}\n\n"


@router.get("/{conversation_id}/stream")
async def stream_message(
    conversation_id: UUID,
    pending: UUID,
    user: EntitledDbUser,
    session: DbSession,
) -> StreamingResponse:
    """SSE replay for a completed assistant message (blocking POST already ran the turn)."""
    service = ConversationService(session)
    conv = await service.get(user.id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    placeholder = await session.get(Message, pending)
    if placeholder is None or placeholder.conversation_id != conv.id:
        raise HTTPException(status_code=404, detail="Pending message not found")
    if placeholder.role != "assistant":
        raise HTTPException(status_code=400, detail="Not an assistant message")

    meta = placeholder.meta_ or {}

    async def _replay() -> AsyncIterator[str]:
        if meta.get("status") != "done":
            yield _format_event(
                SseEvent(
                    event_type="error",
                    data={"message": "Assistant message is not complete yet"},
                )
            )
            return
        yield _format_event(
            SseEvent(
                event_type="done",
                data={
                    "message_id": str(placeholder.id),
                    "tokens_used": meta.get("tokens_used", 0),
                    "cost_cents": meta.get("cost_cents", 0),
                },
            )
        )

    return StreamingResponse(_replay(), media_type="text/event-stream")
