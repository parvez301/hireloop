from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from hireloop.core.evaluation.job_parser import JobParseError
from hireloop.core.llm.errors import LLMQuotaError, LLMTimeoutError
from hireloop.logging import get_logger
from hireloop.services.rate_limit import RateLimitError

log = get_logger("hireloop.errors")


def _sanitize_validation_errors(errors: list[Any]) -> list[Any]:
    """Make Pydantic/FastAPI validation errors JSON-serializable (ctx may hold exceptions)."""
    out: list[Any] = []
    for err in errors:
        if not isinstance(err, dict):
            out.append(err)
            continue
        item = {k: v for k, v in err.items() if k != "ctx"}
        ctx = err.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {
                k: (str(v) if isinstance(v, BaseException) else v) for k, v in ctx.items()
            }
        out.append(item)
    return out


HTTP_CODE_TO_ERROR_CODE: dict[int, str] = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "UPSTREAM_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class AppError(HTTPException):
    """Application-specific error with a machine-readable code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


def _build_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    log.warning(
        "app_error",
        request_id=request_id,
        code=exc.code,
        status_code=exc.status_code,
        message=exc.message,
    )
    return _build_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    code = HTTP_CODE_TO_ERROR_CODE.get(exc.status_code, "INTERNAL_ERROR")
    return _build_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail) if exc.detail else "",
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return _build_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        request_id=request_id,
        details={"errors": _sanitize_validation_errors(list(exc.errors()))},
    )


async def job_parse_error_handler(request: Request, exc: JobParseError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return _build_response(
        status_code=422,
        code="JOB_PARSE_FAILED",
        message=str(exc),
        request_id=request_id,
        details=dict(exc.details) if exc.details else None,
    )


async def llm_timeout_handler(request: Request, exc: LLMTimeoutError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return _build_response(
        status_code=504,
        code="LLM_TIMEOUT",
        message=str(exc),
        request_id=request_id,
        details=exc.details or None,
    )


async def llm_quota_handler(request: Request, exc: LLMQuotaError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return _build_response(
        status_code=503,
        code="LLM_QUOTA_EXCEEDED",
        message=str(exc),
        request_id=request_id,
        details=exc.details or None,
    )


async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    resp = _build_response(
        status_code=429,
        code="RATE_LIMITED",
        message=str(exc),
        request_id=request_id,
    )
    resp.headers["Retry-After"] = str(max(1, int(exc.retry_after_s)))
    return resp


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    log.exception("unhandled_error", request_id=request_id)
    return _build_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        request_id=request_id,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(JobParseError, job_parse_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(LLMTimeoutError, llm_timeout_handler)  # type: ignore[arg-type]
    app.add_exception_handler(LLMQuotaError, llm_quota_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitError, rate_limit_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
