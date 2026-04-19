"""
Central API error responses: consistent JSON shape, no stack traces to clients.
"""
from typing import Any

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import HTTPException

from config import settings

logger = structlog.get_logger()


def _client_safe_detail(detail: Any) -> str | list | dict:
    """Normalize FastAPI detail for JSON (never forward arbitrary objects as opaque blobs)."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return detail
    if isinstance(detail, dict):
        return detail
    return "Request could not be processed."


def register_exception_handlers(app) -> None:
    """Register production-safe handlers (call after app = FastAPI(...))."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code = f"http_{exc.status_code}"
        body = {
            "detail": _client_safe_detail(exc.detail),
            "code": code,
            "error": _client_safe_detail(exc.detail),
        }
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "request_validation_failed",
            path=request.url.path,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "code": "validation_error",
                "error": "Invalid request body or parameters.",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            exc_type=type(exc).__name__,
        )
        if settings.debug:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": str(exc),
                    "code": "internal_error",
                    "error": str(exc),
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred. Please try again later.",
                "code": "internal_error",
                "error": "An internal error occurred. Please try again later.",
            },
        )
