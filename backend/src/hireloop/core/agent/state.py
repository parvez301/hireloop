"""AgentState — LangGraph typed dict for a single conversation turn."""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    # Conversation history
    messages: Annotated[list[BaseMessage], add]

    # User context
    user_id: str
    conversation_id: str
    profile_summary: dict[str, Any]
    subscription_status: Literal["trial", "active", "expired"]
    trial_days_remaining: int | None

    # Current turn classification
    classified_intent: str | None

    # Accumulators
    cards: list[dict[str, Any]]
    model_calls: list[dict[str, Any]]
    tokens_used: int
