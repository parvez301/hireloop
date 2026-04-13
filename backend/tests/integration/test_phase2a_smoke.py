"""Lightweight import/smoke checks for Phase 2a agent + conversations wiring."""


def test_conversations_router_registered():
    from hireloop.main import app

    assert any(getattr(r, "path", "").startswith("/api/v1/conversations") for r in app.routes)
    assert any(getattr(r, "path", "").startswith("/api/v1/billing") for r in app.routes)
    assert any("/webhooks/stripe" in getattr(r, "path", "") for r in app.routes)


def test_agent_runner_importable():
    from hireloop.core.agent.runner import run_turn

    assert callable(run_turn)
