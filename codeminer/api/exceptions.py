"""Global exception handlers for FastAPI application."""

from logging import getLogger
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers.

    Handlers:
    - HTTPException: 4xx responses
    - RequestValidationError: 422 responses
    - Exception: 500 responses
    - FileNotFoundError: 404 responses

    Args:
        app: FastAPI application
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unhandled exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(
        request: Request, exc: FileNotFoundError
    ) -> JSONResponse:
        """Handle file not found errors."""
        logger.warning(f"File not found: {exc}")
        return JSONResponse(status_code=404, content={"error": str(exc)})

    logger.info("Exception handlers registered")
