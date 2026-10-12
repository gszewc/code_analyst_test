"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .exceptions import register_exception_handlers
from .routes.health import router as health_router
from .routes.projects import router as projects_router
from .routes.files import router as files_router
from .routes.analysis import router as analysis_router
from .routes.graph import router as graph_router
from .routes.languages import router as languages_router
from .routes.config import router as config_router
from ..config import settings
from ..logging_config import setup_logging
from .. import container

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:
    - Setup logging
    - Initialize DI container
    - Validate configuration

    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # Startup
    logger.info("Starting up Legacy Code Analysis API")

    # Setup logging
    setup_logging()

    # Initialize container
    container.initialize_container()

    # Validate configuration
    try:
        settings.validate_on_startup()
        logger.info("Configuration validated")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    logger.info(f"API started on {settings.api_host}:{settings.api_port}")

    yield

    # Shutdown
    logger.info("Shutting down Legacy Code Analysis API")
    container.shutdown_container()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Legacy Code Analysis API - Analyze and visualize code structure",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Register exception handlers
register_exception_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(languages_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/", tags=["API"])
async def api_root():
    """API v1 root endpoint."""
    return {
        "version": "v1",
        "endpoints": {
            "health": "/api/v1/health",
            "projects": "/api/v1/projects",
            "files": "/api/v1/projects/{id}/files",
            "analysis": "/api/v1/analysis",
            "graph": "/api/v1/projects/{id}/nodes",
            "search": "/api/v1/projects/{id}/search",
        },
    }
