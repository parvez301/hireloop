from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from hireloop.api import (
    applications,
    auth,
    batch_runs,
    briefing,
    billing,
    conversations,
    cv_outputs,
    evaluations,
    feedback,
    health,
    interview_preps,
    jobs,
    negotiations,
    onboarding,
    profile,
    scan_configs,
    scan_runs,
    star_stories,
    stripe_webhooks,
)
from hireloop.api.errors import register_error_handlers
from hireloop.api.inngest import mount_inngest
from hireloop.config import get_settings
from hireloop.logging import configure_logging, get_logger


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ = app
    configure_logging()
    log = get_logger("hireloop.main")
    settings = get_settings()
    log.info("startup", environment=settings.environment)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HireLoop API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    register_error_handlers(app)

    @app.get("/healthz")
    async def healthz_probe() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(profile.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(evaluations.router, prefix="/api/v1")
    app.include_router(cv_outputs.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")
    app.include_router(billing.router, prefix="/api/v1")
    app.include_router(stripe_webhooks.router, prefix="/api/v1")
    app.include_router(scan_configs.router, prefix="/api/v1")
    app.include_router(scan_runs.router, prefix="/api/v1")
    app.include_router(batch_runs.router, prefix="/api/v1")
    app.include_router(applications.router, prefix="/api/v1")
    app.include_router(interview_preps.router, prefix="/api/v1")
    app.include_router(negotiations.router, prefix="/api/v1")
    app.include_router(briefing.router, prefix="/api/v1")
    app.include_router(onboarding.router, prefix="/api/v1")
    app.include_router(star_stories.router, prefix="/api/v1")
    app.include_router(feedback.router, prefix="/api/v1")

    mount_inngest(app)

    return app


app = create_app()
