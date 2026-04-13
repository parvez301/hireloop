"""Runner: loads conversation, classifies, routes, persists, records usage."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.agent.classifier import classify_node
from hireloop.core.agent.graph import route_node
from hireloop.core.agent.prompts import OFF_TOPIC_RESPONSE, PROMPT_INJECTION_RESPONSE
from hireloop.core.agent.state import AgentState
from hireloop.core.agent.tools import ToolRuntime
from hireloop.core.agent.usage import record_turn_usage
from hireloop.models.conversation import Conversation, Message
from hireloop.models.profile import Profile
from hireloop.models.user import User
from hireloop.schemas.agent import SseEvent
from hireloop.services.subscription import (
    agent_subscription_fields,
    ensure_subscription,
    utc_now,
)

EventEmitter = Callable[[SseEvent], Awaitable[None]]


async def run_turn(
    *,
    session: AsyncSession,
    user: User,
    conversation: Conversation,
    user_message_text: str,
    assistant_message_id: UUID,
    emit: EventEmitter | None = None,
) -> Message:
    settings = get_settings()

    user_row = Message(
        conversation_id=conversation.id,
        role="user",
        content=user_message_text,
    )
    session.add(user_row)
    await session.flush()

    history = await _load_history(session, conversation.id, settings.agent_max_history_messages)
    profile_summary = await _load_profile_summary(session, user.id)

    sub = await ensure_subscription(session, user.id, settings)
    sub_status, trial_days = agent_subscription_fields(sub, utc_now())

    state: AgentState = {
        "messages": history,
        "user_id": str(user.id),
        "conversation_id": str(conversation.id),
        "profile_summary": profile_summary,
        "subscription_status": sub_status,
        "trial_days_remaining": trial_days,
        "classified_intent": None,
        "cards": [],
        "model_calls": [],
        "tokens_used": 0,
    }

    classifier_out = await classify_node(state)
    if "classified_intent" in classifier_out:
        state["classified_intent"] = classifier_out["classified_intent"]
    if "model_calls" in classifier_out:
        state["model_calls"] = classifier_out["model_calls"]
    intent = state["classified_intent"]
    if emit:
        await emit(SseEvent(event_type="classifier", data={"intent": intent}))

    if intent == "OFF_TOPIC":
        final_text = OFF_TOPIC_RESPONSE
    elif intent == "PROMPT_INJECTION":
        final_text = PROMPT_INJECTION_RESPONSE
    else:
        runtime = ToolRuntime(user_id=user.id, session=session)
        if emit and intent in ("EVALUATE_JOB", "OPTIMIZE_CV"):
            await emit(SseEvent(event_type="tool_start", data={"tool": intent.lower()}))
        route_out = await route_node(state, runtime)
        if "messages" in route_out:
            state["messages"] = list(state["messages"]) + route_out["messages"]
        if "cards" in route_out:
            state["cards"] = route_out["cards"]
        if "model_calls" in route_out:
            state["model_calls"] = route_out["model_calls"]
        final_ai = state["messages"][-1] if state["messages"] else AIMessage(content="")
        final_text = getattr(final_ai, "content", "") or ""
        if emit:
            for card in state.get("cards", []):
                await emit(SseEvent(event_type="tool_end", data={"tool": card["type"], "ok": True}))
                await emit(SseEvent(event_type="card", data=card))

    assistant_row = await session.get(Message, assistant_message_id)
    model_calls = state.get("model_calls", [])
    total_tokens = sum(c.get("tokens_used", 0) or 0 for c in model_calls)
    total_cost = sum(c.get("cost_cents", 0) or 0 for c in model_calls)

    if assistant_row is None:
        assistant_row = Message(
            id=assistant_message_id,
            conversation_id=conversation.id,
            role="assistant",
            content=final_text,
            cards=state.get("cards") or None,
            meta_={
                "status": "done",
                "classifier_intent": intent,
                "tokens_used": total_tokens,
                "cost_cents": total_cost,
            },
        )
        session.add(assistant_row)
    else:
        assistant_row.content = final_text
        assistant_row.cards = state.get("cards") or None
        assistant_row.meta_ = {
            "status": "done",
            "classifier_intent": intent,
            "tokens_used": total_tokens,
            "cost_cents": total_cost,
        }

    await record_turn_usage(session, user.id, model_calls)
    await session.flush()

    if emit:
        await emit(
            SseEvent(
                event_type="done",
                data={
                    "message_id": str(assistant_row.id),
                    "tokens_used": total_tokens,
                    "cost_cents": total_cost,
                },
            )
        )

    return assistant_row


async def _load_history(session: AsyncSession, conversation_id: UUID, limit: int) -> list[Any]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    rows = list(reversed(rows))
    out: list[Any] = []
    for r in rows:
        if r.role == "user":
            out.append(HumanMessage(content=r.content))
        elif r.role == "assistant":
            meta = r.meta_ or {}
            if meta.get("status") == "running" and not (r.content or "").strip():
                continue
            out.append(AIMessage(content=r.content))
    return out


async def _load_profile_summary(session: AsyncSession, user_id: UUID) -> dict[str, Any]:
    stmt = select(Profile).where(Profile.user_id == user_id)
    profile = (await session.execute(stmt)).scalar_one_or_none()
    if profile is None:
        return {}
    parsed = profile.parsed_resume_json or {}
    return {
        "skills": list(parsed.get("skills", []))[:20],
        "years_experience": parsed.get("total_years_experience"),
        "target_roles": list(profile.target_roles or []),
        "target_locations": list(profile.target_locations or []),
    }
