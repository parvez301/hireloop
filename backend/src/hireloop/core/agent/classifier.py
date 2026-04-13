"""L0 classifier node — Gemini Flash intent classification."""

from __future__ import annotations

from typing import Any

from hireloop.core.agent.state import AgentState
from hireloop.core.llm.gemini_client import classify_intent


async def classify_node(state: AgentState) -> dict[str, Any]:
    messages = state["messages"]
    if not messages:
        return {"classified_intent": "CAREER_GENERAL"}

    last = messages[-1]
    content = getattr(last, "content", "")
    if isinstance(content, list):
        content = " ".join(str(x) for x in content)
    intent = await classify_intent(str(content))

    model_calls = list(state.get("model_calls", []))
    model_calls.append(
        {
            "event_type": "classify",
            "module": "agent",
            "model": "gemini-2.0-flash-exp",
            "tokens_used": 50,
            "cost_cents": 1,
        }
    )
    return {
        "classified_intent": intent,
        "model_calls": model_calls,
    }
