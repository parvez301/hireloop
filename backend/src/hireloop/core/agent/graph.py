"""LangGraph graph builder and route handlers.

The graph intentionally does NOT use langgraph ToolNode because our tool
implementations need a runtime context (DB session, user id) that isn't
expressible via the standard tool protocol. Instead we have a simple
route_node → tools_node → respond_node flow, plus a short-circuit for
OFF_TOPIC / PROMPT_INJECTION / not-yet-implemented intents.
"""

from __future__ import annotations

import json as _json
from typing import Any

from langchain_core.messages import AIMessage

from hireloop.config import get_settings
from hireloop.core.agent.prompts import (
    NOT_YET_AVAILABLE_TEMPLATES,
    SYSTEM_PROMPT,
)
from hireloop.core.agent.state import AgentState
from hireloop.core.agent.tools import (
    ToolRuntime,
    build_interview_prep_tool,
    evaluate_job_tool,
    generate_negotiation_playbook_tool,
    optimize_cv_tool,
    start_batch_evaluation_tool,
    start_job_scan_tool,
)
from hireloop.core.llm.anthropic_client import complete_with_cache


async def route_node(state: AgentState, runtime: ToolRuntime) -> dict[str, Any]:
    """Call Claude once to either answer directly or produce a tool call."""
    intent = state.get("classified_intent")

    if intent in NOT_YET_AVAILABLE_TEMPLATES:
        return {
            "messages": [AIMessage(content=NOT_YET_AVAILABLE_TEMPLATES[intent])],
        }

    settings = get_settings()
    user_msg = state["messages"][-1]
    user_content = getattr(user_msg, "content", "")

    tool_manifest = """Available tools (you may call at most ONE):

{"call": "evaluate_job", "args": {"job_url": "..."}} — when the user pastes a URL
{"call": "evaluate_job", "args": {"job_description": "..."}} — when the user pastes raw JD text
{"call": "optimize_cv", "args": {"job_id": "<uuid>"}} — when the user wants a tailored CV for a prior evaluation
{"call": "start_job_scan", "args": {}} — when the user wants to find/discover jobs across their default scan config
{"call": "start_batch_evaluation", "args": {"scan_run_id": "<uuid>"}} — to evaluate all results from a recent scan
{"call": "start_batch_evaluation", "args": {"job_urls": ["https://...", ...]}} — to evaluate a list of URLs
{"call": "start_batch_evaluation", "args": {"job_ids": ["<uuid>", ...]}} — to evaluate existing jobs
{"call": "build_interview_prep", "args": {"job_id": "<uuid>"}} — to prep for a specific job interview
{"call": "build_interview_prep", "args": {"custom_role": "<role description>"}} — generic prep for a role
{"call": "generate_negotiation_playbook", "args": {"job_id": "<uuid>"}} — when the user has an offer to negotiate

If no tool is needed (career_general questions, follow-ups), respond naturally.

To call a tool, reply with EXACTLY this structure and nothing else:
TOOL_CALL: {"call": "...", "args": {...}}

Otherwise, reply normally with conversational text."""

    user_block = f"User message: {user_content}\n\n{tool_manifest}"

    result = await complete_with_cache(
        system=SYSTEM_PROMPT,
        cacheable_blocks=[tool_manifest],
        user_block=user_block,
        model=settings.claude_model,
        max_tokens=800,
        timeout_s=settings.llm_evaluation_timeout_s,
    )

    model_calls = list(state.get("model_calls", []))
    model_calls.append(
        {
            "event_type": "respond",
            "module": "agent",
            "model": result.model,
            "tokens_used": result.usage.total_tokens,
            "cost_cents": result.usage.cost_cents(result.model),
        }
    )

    text = result.text.strip()
    if text.startswith("TOOL_CALL:"):
        raw = text[len("TOOL_CALL:") :].strip()
        try:
            call = _json.loads(raw)
        except Exception:
            return {
                "messages": [AIMessage(content=text)],
                "model_calls": model_calls,
            }

        tool_name = call.get("call")
        args = call.get("args", {}) or {}
        if tool_name == "evaluate_job":
            tool_result = await evaluate_job_tool(runtime, **args)
        elif tool_name == "optimize_cv":
            tool_result = await optimize_cv_tool(runtime, **args)
        elif tool_name == "start_job_scan":
            tool_result = await start_job_scan_tool(runtime, **args)
        elif tool_name == "start_batch_evaluation":
            tool_result = await start_batch_evaluation_tool(runtime, **args)
        elif tool_name == "build_interview_prep":
            tool_result = await build_interview_prep_tool(runtime, **args)
        elif tool_name == "generate_negotiation_playbook":
            tool_result = await generate_negotiation_playbook_tool(runtime, **args)
        else:
            tool_result = {
                "ok": False,
                "error_code": "UNKNOWN_TOOL",
                "message": f"Tool {tool_name} is not available",
            }

        cards = list(state.get("cards", []))
        if tool_result.get("ok"):
            cards.append(tool_result["card"])
            reply_text = _summary_for_card(tool_result["card"])
        else:
            reply_text = (
                f"I ran into an issue running that: {tool_result.get('message', 'unknown error')}. "
                "Want to try something else?"
            )

        return {
            "messages": [AIMessage(content=reply_text)],
            "cards": cards,
            "model_calls": model_calls,
        }

    return {
        "messages": [AIMessage(content=text)],
        "model_calls": model_calls,
    }


def _summary_for_card(card: dict[str, Any]) -> str:
    if card["type"] == "evaluation":
        d = card["data"]
        return (
            f"I evaluated **{d['job_title']}** at {d.get('company') or 'the company'}. "
            f"Overall grade: **{d['overall_grade']}** ({d['recommendation'].replace('_', ' ')})."
        )
    if card["type"] == "cv_output":
        d = card["data"]
        return f"I tailored your CV for **{d['job_title']}**. The PDF is ready to download."
    if card["type"] == "scan_progress":
        d = card["data"]
        return (
            f"Starting a scan across {d.get('companies_count', '?')} companies. "
            "I'll let you know when it's done — check the progress card below."
        )
    if card["type"] == "batch_progress":
        d = card["data"]
        return (
            f"Starting batch evaluation on {d.get('total', '?')} jobs. "
            "L0 → L1 → L2 funnel — watch the progress card below."
        )
    if card["type"] == "interview_prep":
        d = card["data"]
        return (
            f"I built interview prep ({d.get('question_count', 0)} questions). "
            "Review the card below for practice questions and what to ask them."
        )
    if card["type"] == "negotiation":
        d = card["data"]
        return (
            f"Here's a negotiation playbook for **{d.get('job_title', 'the role')}**. "
            "Open the card for scripts and counter-offer ideas."
        )
    return "Done."
