"""
Data models for Database Layer.

This module defines Pydantic models for database configuration, entities,
and result objects used across the database layer.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, Optional
from datetime import datetime

from ..datetime_utils import utc_now


class DatabaseConfig(BaseModel):
    """Database configuration.

    Attributes:
        sqlite_path: Path to SQLite database file or ':memory:' for in-memory
        neo4j_uri: Neo4j Bolt protocol URI (e.g., 'bolt://localhost:7687')
        neo4j_user: Neo4j authentication username
        neo4j_password: Neo4j authentication password
        neo4j_pool_size: Neo4j connection pool size
        neo4j_max_retry: Maximum retry attempts for failed operations
    """

    sqlite_path: str = Field(
        default=":memory:", description="SQLite database path (:memory: for in-memory)"
    )
    neo4j_uri: str = Field(
        default="bolt://localhost:7687", description="Neo4j Bolt URI"
    )
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password", description="Neo4j password")
    neo4j_pool_size: int = Field(
        default=50, ge=1, le=200, description="Neo4j connection pool size"
    )
    neo4j_max_retry: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )
    model_config = ConfigDict(env_prefix="", env_file=".env")


class Project(BaseModel):
    """Project entity for SQLite storage.

    Attributes:
        id: Project UUID
        name: Project name (unique, alphanumeric/hyphen/underscore only)
        description: Optional project description
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")
    description: str = Field(default="", description="Project description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class Analysis(BaseModel):
    """Analysis run entity for SQLite storage.

    Tracks parsing/analysis runs for a project.

    Attributes:
        id: Analysis UUID
        project_id: Reference to parent project
        started_at: Analysis start time
        completed_at: Completion time (None if in progress)
        files_count: Number of files processed
        nodes_count: Number of nodes stored
        relationships_count: Number of relationships stored
        status: Analysis status (pending|running|completed|failed)
        error_message: Error message if failed
    """

    id: str = Field(..., description="Analysis UUID")
    project_id: str = Field(..., description="Reference to project")
    started_at: datetime = Field(..., description="Analysis start time")
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion time"
    )
    files_count: int = Field(default=0, description="Number of files processed")
    nodes_count: int = Field(default=0, description="Number of nodes stored")
    relationships_count: int = Field(
        default=0, description="Number of relationships stored"
    )
    status: str = Field(
        default="pending", description="pending|running|completed|failed"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )


class StorageResult(BaseModel):
    """Result of a storage operation.

    Attributes:
        files_stored: Number of files stored
        nodes_stored: Number of nodes stored
        relationships_stored: Number of relationships stored
        duration_ms: Storage duration in milliseconds
        summary: Optional structured run-level summary (populated by UNWIND batching path)
    """

    files_stored: int = Field(default=0, description="Number of files stored")
    nodes_stored: int = Field(default=0, description="Number of nodes stored")
    relationships_stored: int = Field(
        default=0, description="Number of relationships stored"
    )
    duration_ms: float = Field(
        default=0.0, description="Storage duration in milliseconds"
    )
    summary: Optional[Any] = Field(
        default=None,
        description="Structured run-level summary (StorageResultSummary) from batching path",
    )


class GraphSummary(BaseModel):
    """Summary of graph data for a project.

    Attributes:
        total_nodes: Total number of nodes
        nodes_by_type: Node count grouped by type
        total_relationships: Total number of relationships
        relationships_by_type: Relationship count grouped by type
    """

    total_nodes: int = Field(default=0, description="Total number of nodes")
    nodes_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Node count grouped by type"
    )
    total_relationships: int = Field(
        default=0, description="Total number of relationships"
    )
    relationships_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Relationship count grouped by type"
    )


class HealthStatus(BaseModel):
    """Database health status.

    Attributes:
        sqlite_healthy: True if SQLite connection is healthy
        neo4j_healthy: True if Neo4j connection is healthy
        overall_healthy: True if all connections are healthy
        timestamp: Health check timestamp
        error: Optional error message if unhealthy
    """

    sqlite_healthy: bool = Field(default=False, description="SQLite health status")
    neo4j_healthy: bool = Field(default=False, description="Neo4j health status")
    overall_healthy: bool = Field(default=False, description="Overall health status")
    timestamp: datetime = Field(default_factory=utc_now, description="Check timestamp")
    error: Optional[str] = Field(default=None, description="Error message if unhealthy")
