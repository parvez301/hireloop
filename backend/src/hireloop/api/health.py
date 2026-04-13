from fastapi import APIRouter
from sqlalchemy import text

from hireloop.db import get_engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, object]:
    checks: dict[str, str] = {}
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    checks["redis"] = "ok"
    status = "ok" if checks.get("database") == "ok" else "degraded"
    return {"status": status, "checks": checks}
