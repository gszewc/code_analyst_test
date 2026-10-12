"""
Graph cleanup utilities for Neo4j database.

Provides utility functions to delete nodes and relationships from Neo4j
filtered by project_id.
"""

import logging
from typing import Optional

from .graph_storage import GraphStorage, GraphStorageError
from .neo4j_manager import Neo4jConnectionManager
from .models import DatabaseConfig

logger = logging.getLogger(__name__)


def delete_all_graph_data_by_project(
    project_id: str,
    config: Optional[DatabaseConfig] = None,
    neo4j_manager: Optional[Neo4jConnectionManager] = None
) -> int:
    """
    Delete all graph data (nodes and relationships) for a project.

    This is a convenience function that creates the necessary connections,
    performs the deletion, and cleans up resources.

    Args:
        project_id: Project UUID to delete data for
        config: Optional DatabaseConfig. If not provided, uses default config.
        neo4j_manager: Optional existing Neo4jConnectionManager. If provided,
                      config is ignored and this manager is used instead.

    Returns:
        Total number of deleted nodes and relationships

    Raises:
        GraphStorageError: If deletion fails

    Example:
        >>> from codeminer.database.models import DatabaseConfig
        >>> config = DatabaseConfig(neo4j_uri='bolt://localhost:7687', ...)
        >>> deleted = delete_all_graph_data_by_project('project-uuid-123', config=config)
        >>> print(f"Deleted {deleted} items")
    """
    manager = neo4j_manager
    should_close = False

    try:
        # Create manager if not provided
        if manager is None:
            config = config or DatabaseConfig()
            manager = Neo4jConnectionManager(config)
            should_close = True

        # Perform deletion
        storage = GraphStorage(manager)
        deleted = storage.delete_by_project(project_id)

        logger.info(f'Deleted {deleted} items for project {project_id}')
        return deleted

    finally:
        # Close manager if we created it
        if should_close and manager:
            manager.close()

def delete_all_graph_data(
    config: Optional[DatabaseConfig] = None,
    neo4j_manager: Optional[Neo4jConnectionManager] = None
) -> int:
    """
    Delete all graph data (nodes and relationships).

    This is a convenience function that creates the necessary connections,
    performs the deletion, and cleans up resources.

    Args:
        config: Optional DatabaseConfig. If not provided, uses default config.
        neo4j_manager: Optional existing Neo4jConnectionManager. If provided,
                      config is ignored and this manager is used instead.

    Returns:
        Total number of deleted nodes and relationships

    Raises:
        GraphStorageError: If deletion fails

    Example:
        >>> from codeminer.database.models import DatabaseConfig
        >>> config = DatabaseConfig(neo4j_uri='bolt://localhost:7687', ...)
        >>> deleted = delete_all_graph_data('project-uuid-123', config=config)
        >>> print(f"Deleted {deleted} items")
    """
    manager = neo4j_manager
    should_close = False

    try:
        # Create manager if not provided
        if manager is None:
            config = config or DatabaseConfig()
            manager = Neo4jConnectionManager(config)
            should_close = True

        # Perform deletion
        storage = GraphStorage(manager)
        deleted = storage.delete_all()

        logger.info(f'Deleted {deleted} items from the graph')
        return deleted

    finally:
        # Close manager if we created it
        if should_close and manager:
            manager.close()


def delete_nodes_only(
    project_id: str,
    config: Optional[DatabaseConfig] = None,
    neo4j_manager: Optional[Neo4jConnectionManager] = None
) -> int:
    """
    Delete only AST nodes for a project (relationships are auto-deleted via DETACH).

    Args:
        project_id: Project UUID to delete data for
        config: Optional DatabaseConfig. If not provided, uses default config.
        neo4j_manager: Optional existing Neo4jConnectionManager.

    Returns:
        Number of deleted nodes

    Raises:
        GraphStorageError: If deletion fails

    Example:
        >>> deleted = delete_nodes_only('project-uuid-123', config=config)
        >>> print(f"Deleted {deleted} nodes")
    """
    manager = neo4j_manager
    should_close = False

    try:
        if manager is None:
            config = config or DatabaseConfig()
            manager = Neo4jConnectionManager(config)
            should_close = True

        storage = GraphStorage(manager)
        deleted = storage.delete_nodes_by_project(project_id)

        logger.info(f'Deleted {deleted} nodes for project {project_id}')
        return deleted

    finally:
        if should_close and manager:
            manager.close()


def delete_relationships_only(
    project_id: str,
    config: Optional[DatabaseConfig] = None,
    neo4j_manager: Optional[Neo4jConnectionManager] = None
) -> int:
    """
    Delete only relationships for a project (nodes are preserved).

    Args:
        project_id: Project UUID to delete data for
        config: Optional DatabaseConfig. If not provided, uses default config.
        neo4j_manager: Optional existing Neo4jConnectionManager.

    Returns:
        Number of deleted relationships

    Raises:
        GraphStorageError: If deletion fails

    Example:
        >>> deleted = delete_relationships_only('project-uuid-123', config=config)
        >>> print(f"Deleted {deleted} relationships")
    """
    manager = neo4j_manager
    should_close = False

    try:
        if manager is None:
            config = config or DatabaseConfig()
            manager = Neo4jConnectionManager(config)
            should_close = True

        storage = GraphStorage(manager)
        deleted = storage.delete_relationships_by_project(project_id)

        logger.info(f'Deleted {deleted} relationships for project {project_id}')
        return deleted

    finally:
        if should_close and manager:
            manager.close()


def delete_nodes_by_type(
    project_id: str,
    node_types: list[str],
    config: Optional[DatabaseConfig] = None,
    neo4j_manager: Optional[Neo4jConnectionManager] = None
) -> int:
    """
    Delete nodes of specific type(s) for a project.

    Args:
        project_id: Project UUID to delete data for
        node_types: List of node types to delete (e.g., ['Method', 'Variable'])
        config: Optional DatabaseConfig. If not provided, uses default config.
        neo4j_manager: Optional existing Neo4jConnectionManager.

    Returns:
        Number of deleted nodes

    Raises:
        GraphStorageError: If deletion fails

    Example:
        >>> deleted = delete_nodes_by_type(
        ...     'project-uuid-123',
        ...     node_types=['Method', 'Function'],
        ...     config=config
        ... )
        >>> print(f"Deleted {deleted} method/function nodes")
    """
    manager = neo4j_manager
    should_close = False

    try:
        if manager is None:
            config = config or DatabaseConfig()
            manager = Neo4jConnectionManager(config)
            should_close = True

        storage = GraphStorage(manager)
        deleted = storage.delete_nodes_by_type(project_id, node_types)

        logger.info(
            f'Deleted {deleted} nodes of type(s) {node_types} '
            f'for project {project_id}'
        )
        return deleted

    finally:
        if should_close and manager:
            manager.close()


def delete_relationships_by_type(
    project_id: str,
    relationship_types: list[str],
    config: Optional[DatabaseConfig] = None,
    neo4j_manager: Optional[Neo4jConnectionManager] = None
) -> int:
    """
    Delete relationships of specific type(s) for a project.

    Args:
        project_id: Project UUID to delete data for
        relationship_types: List of relationship types to delete
                          (e.g., ['CALLS', 'DEPENDS_ON'])
        config: Optional DatabaseConfig. If not provided, uses default config.
        neo4j_manager: Optional existing Neo4jConnectionManager.

    Returns:
        Number of deleted relationships

    Raises:
        GraphStorageError: If deletion fails

    Example:
        >>> deleted = delete_relationships_by_type(
        ...     'project-uuid-123',
        ...     relationship_types=['CALLS', 'DEPENDS_ON'],
        ...     config=config
        ... )
        >>> print(f"Deleted {deleted} call/dependency relationships")
    """
    manager = neo4j_manager
    should_close = False

    try:
        if manager is None:
            config = config or DatabaseConfig()
            manager = Neo4jConnectionManager(config)
            should_close = True

        storage = GraphStorage(manager)
        deleted = storage.delete_relationships_by_type(
            project_id, relationship_types
        )

        logger.info(
            f'Deleted {deleted} relationships of type(s) {relationship_types} '
            f'for project {project_id}'
        )
        return deleted

    finally:
        if should_close and manager:
            manager.close()


class GraphCleanup:
    """
    Context manager for graph cleanup operations.

    Provides a convenient way to perform multiple cleanup operations
    while managing database connections efficiently.

    Example:
        >>> config = DatabaseConfig()
        >>> with GraphCleanup(config) as cleanup:
        ...     # Delete all data for a project
        ...     cleanup.delete_all('project-id-123')
        ...
        ...     # Or delete selectively
        ...     cleanup.delete_nodes_by_type('project-id-456', ['Method'])
        ...     cleanup.delete_relationships_by_type('project-id-789', ['CALLS'])
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize graph cleanup context manager.

        Args:
            config: Optional DatabaseConfig. If not provided, uses default.
        """
        self.config = config or DatabaseConfig()
        self._manager: Optional[Neo4jConnectionManager] = None
        self._storage: Optional[GraphStorage] = None

    def __enter__(self) -> 'GraphCleanup':
        """Enter context and initialize connections."""
        self._manager = Neo4jConnectionManager(self.config)
        self._storage = GraphStorage(self._manager)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and cleanup resources."""
        if self._manager:
            self._manager.close()
            self._manager = None
            self._storage = None
    
    def delete_all(self) -> int:
        """
        Delete all graph data 

        This is a convenience method that calls delete_all

        Returns:
            Total number of deleted items
        """
        if self._storage is None:
            raise GraphStorageError('Storage not initialized')
        return self._storage.delete_all()  

    def delete_all_by_project(self, project_id: str) -> int:
        """
        Delete all graph data for a project.

        Args:
            project_id: Project UUID

        Returns:
            Total number of deleted items
        """
        if self._storage is None:
            raise GraphStorageError('Storage not initialized')
        return self._storage.delete_by_project(project_id)

    def delete_nodes(self, project_id: str) -> int:
        """
        Delete only nodes for a project.

        Args:
            project_id: Project UUID

        Returns:
            Number of deleted nodes
        """
        if self._storage is None:
            raise GraphStorageError('Storage not initialized')
        return self._storage.delete_nodes_by_project(project_id)

    def delete_relationships(self, project_id: str) -> int:
        """
        Delete only relationships for a project.

        Args:
            project_id: Project UUID

        Returns:
            Number of deleted relationships
        """
        if self._storage is None:
            raise GraphStorageError('Storage not initialized')
        return self._storage.delete_relationships_by_project(project_id)

    def delete_nodes_by_type(self, project_id: str, node_types: list[str]) -> int:
        """
        Delete nodes of specific type(s).

        Args:
            project_id: Project UUID
            node_types: List of node types to delete

        Returns:
            Number of deleted nodes
        """
        if self._storage is None:
            raise GraphStorageError('Storage not initialized')
        return self._storage.delete_nodes_by_type(project_id, node_types)

    def delete_relationships_by_type(
        self,
        project_id: str,
        relationship_types: list[str]
    ) -> int:
        """
        Delete relationships of specific type(s).

        Args:
            project_id: Project UUID
            relationship_types: List of relationship types to delete

        Returns:
            Number of deleted relationships
        """
        if self._storage is None:
            raise GraphStorageError('Storage not initialized')
        return self._storage.delete_relationships_by_type(
            project_id, relationship_types
        )
