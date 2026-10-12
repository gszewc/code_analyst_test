"""Graph service for Neo4j graph query operations."""

from logging import getLogger
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..database.graph_storage import GraphStorage
from ..database.models import GraphSummary
from ..database.project_storage import ProjectStorage, ProjectNotFoundError

logger = getLogger(__name__)


class GraphService:
    """
    Service for graph query operations.

    Responsibilities:
    - Node queries with filtering and limiting
    - Relationship queries
    - Node search by name and type
    - Result limiting for performance
    """

    # Default and maximum result limits
    DEFAULT_LIMIT = 1000
    MAX_LIMIT = 10000

    def __init__(
        self,
        graph_storage: GraphStorage,
        project_storage: Optional[ProjectStorage] = None,
    ):
        """
        Initialize graph service.

        Args:
            graph_storage: GraphStorage instance
            project_storage: Optional ProjectStorage instance for project existence checks
        """
        self.graph_storage = graph_storage
        self.project_storage = project_storage
        logger.info("GraphService initialized")

    def get_nodes(
        self,
        project_id: UUID,
        node_type: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
        source_file: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get nodes for a project.

        Args:
            project_id: Project UUID
            node_type: Optional node type filter
            limit: Maximum number of nodes to return
            source_file: Optional source file path filter

        Returns:
            List of node dictionaries

        Raises:
            ValueError: If limit exceeds maximum
        """
        # Validate limit
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit exceeds maximum: {self.MAX_LIMIT}")

        try:
            if node_type:
                logger.debug(
                    f"Querying nodes for project {project_id} with type '{node_type}' and limit {limit}"
                )
                nodes = self.graph_storage.query_nodes_by_type(
                    project_id=str(project_id),
                    node_type=node_type,
                    source_file=source_file,
                    language=language,
                    limit=limit,
                )
            else:
                logger.debug(
                    f"Querying nodes for project {project_id} with limit {limit}"
                )
                nodes = self.graph_storage.query_nodes_by_project(
                    project_id=str(project_id),
                    source_file=source_file,
                    language=language,
                    limit=limit,
                )

            logger.debug(f"Retrieved {len(nodes)} nodes for project {project_id}")
            return nodes
        except Exception as e:
            logger.error(f"Error retrieving nodes: {e}", exc_info=True)
            raise

    def get_node_by_id(
        self,
        project_id: UUID,
        node_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a node by project and node ID.

        Args:
            project_id: Project UUID
            node_id: Node ID

        Returns:
            Node dictionary or None if not found
        """
        try:
            node = self.graph_storage.get_node_by_id(str(project_id), node_id)
            if node:
                logger.debug(f"Retrieved node: {node_id}")
            return node
        except Exception as e:
            logger.error(f"Error retrieving node: {e}", exc_info=True)
            return None

    def get_relationships_for_node(
        self, project_id: UUID, node_id: str, direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a node.

        Args:
            project_id: Project UUID
            node_id: Node ID
            direction: Relationship direction ('incoming', 'outgoing', 'both')

        Returns:
            List of relationship dictionaries
        """
        try:
            relationships = self.graph_storage.get_relationships_for_node(
                project_id=str(project_id), node_id=node_id, direction=direction
            )
            logger.debug(
                f"Retrieved {len(relationships)} relationships for node: {node_id}"
            )
            return relationships
        except Exception as e:
            logger.error(f"Error retrieving relationships: {e}", exc_info=True)
            raise

    def search_nodes(
        self,
        project_id: UUID,
        search_term: str,
        node_type: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        Search nodes by name.

        Args:
            project_id: Project UUID
            search_term: Search term (matched against node name)
            node_type: Optional node type filter
            limit: Maximum number of nodes to return

        Returns:
            List of matching node dictionaries
        """
        # Validate limit
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit exceeds maximum: {self.MAX_LIMIT}")

        try:
            nodes = self.graph_storage.search_nodes(
                project_id=str(project_id),
                search_term=search_term,
                node_type=node_type,
                limit=limit,
            )
            logger.debug(f"Search found {len(nodes)} nodes matching '{search_term}'")
            return nodes
        except Exception as e:
            logger.error(f"Error searching nodes: {e}", exc_info=True)
            raise

    def get_node_count(self, project_id: UUID) -> int:
        """
        Get total node count for a project.

        Args:
            project_id: Project UUID

        Returns:
            Total node count
        """
        try:
            count = self.graph_storage.get_node_count(str(project_id))
            logger.debug(f"Node count for project {project_id}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting nodes: {e}", exc_info=True)
            return 0

    def get_graph_summary(self, project_id: str) -> GraphSummary:
        """Get graph data summary for a project."""
        return self.graph_storage.get_summary(project_id)

    def get_relationship_count(self, project_id: UUID) -> int:
        """
        Get total relationship count for a project.

        Args:
            project_id: Project UUID

        Returns:
            Total relationship count
        """
        try:
            count = self.graph_storage.get_relationship_count(str(project_id))
            logger.debug(f"Relationship count for project {project_id}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting relationships: {e}", exc_info=True)
            return 0

    def get_project_relationships(
        self,
        project_id: UUID,
        types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all relationships for a project with optional type filtering and limit.

        Args:
            project_id: Project UUID
            types: Optional list of relationship type strings to filter by.
                   Empty or omitted means return all types.
            limit: Optional maximum number of relationships to return.
                   Defaults to DEFAULT_LIMIT. Max is MAX_LIMIT.

        Returns:
            List of relationship dictionaries

        Raises:
            ProjectNotFoundError: If the project does not exist
            ValueError: If limit is out of valid range
        """
        # Resolve and validate limit
        effective_limit = limit if limit is not None else self.DEFAULT_LIMIT
        if effective_limit < 1 or effective_limit > self.MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {self.MAX_LIMIT}")

        # Normalize and deduplicate types
        normalized_types: List[str] = []
        if types:
            seen = set()
            for t in types:
                stripped = t.strip()
                if stripped and stripped not in seen:
                    normalized_types.append(stripped)
                    seen.add(stripped)

        # Validate project existence
        if self.project_storage is not None:
            project = self.project_storage.get_project(str(project_id))
            if project is None:
                raise ProjectNotFoundError(f"Project not found: {project_id}")

        try:
            relationships = self.graph_storage.query_project_relationships(
                project_id=str(project_id),
                types=normalized_types if normalized_types else None,
                limit=effective_limit,
            )
            logger.debug(
                f"Retrieved {len(relationships)} relationships for project {project_id}"
            )
            return relationships
        except Exception as e:
            logger.error(f"Error retrieving project relationships: {e}", exc_info=True)
            raise
