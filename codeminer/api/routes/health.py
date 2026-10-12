"""Health check endpoint."""

from logging import getLogger
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ...database.sqlite_manager import SqliteConnectionManager
from ...database.neo4j_manager import Neo4jConnectionManager
from ... import container

logger = getLogger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    version: str
    sqlite: str
    neo4j: Optional[str] = None


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Health check endpoint.

    Checks connectivity to:
    - SQLite database
    - Neo4j database

    Returns:
        HealthStatus with overall status and individual component status
    """
    from ...config import settings

    service_container = container.get_container()

    sqlite_status = "unknown"
    neo4j_status = "unknown"
    overall_status = "healthy"

    # Check SQLite
    try:
        sqlite_manager = service_container.get(SqliteConnectionManager)
        if sqlite_manager.health_check():
            sqlite_status = "connected"
        else:
            sqlite_status = "error: health check failed"
            overall_status = "degraded"
    except Exception as e:
        sqlite_status = f"error: {str(e)}"
        overall_status = "degraded"
        logger.error(f"SQLite health check failed: {e}")

    # Check Neo4j
    try:
        neo4j_manager = service_container.get(Neo4jConnectionManager)
        if neo4j_manager.health_check():
            neo4j_status = "connected"
        else:
            neo4j_status = "error: health check failed"
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as e:
        neo4j_status = f"error: {str(e)}"
        if overall_status == "healthy":
            overall_status = "degraded"
        logger.error(f"Neo4j health check failed: {e}")

    # If both failed, mark as unhealthy
    if sqlite_status.startswith("error") and neo4j_status.startswith("error"):
        overall_status = "unhealthy"

    return HealthStatus(
        status=overall_status,
        version=settings.app_version,
        sqlite=sqlite_status,
        neo4j=neo4j_status,
    )
