"""
Database Layer for Legacy Code Analysis Application.

This package provides database storage and retrieval for AST analysis results,
including SQLite for project metadata and Neo4j for graph storage.
"""

from .sqlite_manager import SqliteConnectionManager
from .neo4j_manager import Neo4jConnectionManager
from .project_storage import ProjectStorage
from .analysis_storage import AnalysisStorage
from .graph_storage import GraphStorage
from .graph_cleanup import (
    delete_all_graph_data,
    delete_nodes_only,
    delete_relationships_only,
    delete_nodes_by_type,
    delete_relationships_by_type,
    GraphCleanup,
)
from .cli import create_cli, main
from .sqlite_initializer import SqliteInitializer
from .neo4j_initializer import Neo4jInitializer
from .models import (
    DatabaseConfig,
    Project,
    Analysis,
    StorageResult,
    GraphSummary,
    HealthStatus,
)

__all__ = [
    # Connection Managers
    'SqliteConnectionManager',
    'Neo4jConnectionManager',
    # Storage
    'ProjectStorage',
    'AnalysisStorage',
    'GraphStorage',
    # Cleanup Utilities
    'delete_all_graph_data',
    'delete_nodes_only',
    'delete_relationships_only',
    'delete_nodes_by_type',
    'delete_relationships_by_type',
    'GraphCleanup',
    # CLI
    'create_cli',
    'main',
    # Initializers
    'SqliteInitializer',
    'Neo4jInitializer',
    # Models
    'DatabaseConfig',
    'Project',
    'Analysis',
    'StorageResult',
    'GraphSummary',
    'HealthStatus',
]
