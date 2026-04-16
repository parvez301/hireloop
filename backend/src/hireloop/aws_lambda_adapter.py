"""AWS Lambda entrypoints: HTTP API (Mangum) and one-off Alembic migrations."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from mangum import Mangum
from mangum.types import LambdaContext

from hireloop.main import create_app

_task_root = os.environ.get("LAMBDA_TASK_ROOT", "/var/task")
_mangum: Mangum | None = None


def handler(event: dict[str, Any], context: LambdaContext) -> Any:
    """API Gateway / Function URL handler."""
    global _mangum
    if _mangum is None:
        _mangum = Mangum(create_app(), lifespan="off")
    return _mangum(event, context)


def migration_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Run `alembic upgrade head`; always returns JSON (never raises)."""
    _ = (event, context)
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", f"{_task_root}/src")
    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=_task_root,
        env=env,
        check=False,
    )
    result: dict[str, Any] = {
        "status": "failed",
        "head": None,
        "stdout": upgrade.stdout,
        "stderr": upgrade.stderr,
        "returncode": upgrade.returncode,
    }
    if upgrade.returncode != 0:
        return result

    current = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        capture_output=True,
        text=True,
        cwd=_task_root,
        env=env,
        check=False,
    )
    head: str | None = None
    if current.returncode == 0 and current.stdout.strip():
        parts = current.stdout.strip().split()
        head = parts[0] if parts else None
    result["status"] = "ok"
    result["head"] = head
    result["stdout"] = upgrade.stdout + ("\n" + current.stdout if current.stdout else "")
    result["stderr"] = upgrade.stderr + ("\n" + current.stderr if current.stderr else "")
    return result
