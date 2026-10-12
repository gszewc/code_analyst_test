"""Graph API routes."""

from logging import getLogger
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from ...services.graph_service import GraphService
from ...database.project_storage import ProjectNotFoundError
from ... import container

logger = getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Graph"])


def get_graph_service() -> GraphService:
    """Get graph service from container."""
    return container.get_container().get(GraphService)


@router.get("/{project_id}/nodes")
async def get_nodes(
    project_id: UUID,
    node_type: Optional[str] = Query(default=None, description="Filter by node type"),
    source_file: Optional[str] = Query(
        default=None, description="Filter by normalized source file path"
    ),
    language: Optional[str] = Query(
        default=None, description="Filter by programming language"
    ),
    limit: int = Query(
        default=1000, ge=1, le=10000, description="Maximum nodes to return"
    ),
    service: GraphService = Depends(get_graph_service),
):
    """
    Get nodes for a project.

    - **project_id**: Project UUID
    - **node_type**: Optional node type filter (e.g., 'Function', 'Class')
    - **language**: Optional language filter (e.g., 'python')
    - **limit**: Maximum nodes to return (default: 1000, max: 10000)

    Returns list of AST nodes.
    """
    try:
        if source_file is not None:
            if (
                source_file.startswith("/")
                or ".." in source_file
                or "\\" in source_file
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid source_file. Use normalized relative paths such as 'application/app.py'",
                )

        nodes = service.get_nodes(
            project_id,
            node_type,
            limit,
            source_file=source_file,
            language=language,
        )
        return {"nodes": nodes, "total": len(nodes), "limit": limit}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving nodes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve nodes")


@router.get("/{project_id}/nodes/{node_id}")
async def get_node_by_id(
    project_id: UUID, node_id: str, service: GraphService = Depends(get_graph_service)
):
    """
    Get node by ID.

    - **project_id**: Project UUID
    - **node_id**: Node ID

    Returns a single node.
    """
    try:
        node = service.get_node_by_id(project_id, node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
        return {"node": node}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving node: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve node")


@router.get("/{project_id}/nodes/{node_id}/relationships")
async def get_relationships_for_node(
    project_id: UUID,
    node_id: str,
    direction: str = Query(
        default="both",
        description="Relationship direction: incoming, outgoing, or both",
    ),
    service: GraphService = Depends(get_graph_service),
):
    """
    Get relationships for a node.

    - **project_id**: Project UUID
    - **node_id**: Node ID
    - **direction**: Relationship direction (incoming, outgoing, both)

    Returns relationships connected to the node.
    """
    try:
        if direction not in ["incoming", "outgoing", "both"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid direction. Must be 'incoming', 'outgoing', or 'both'",
            )

        relationships = service.get_relationships_for_node(project_id, node_id, direction)
        return {"relationships": relationships, "total": len(relationships)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving relationships: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve relationships")


@router.get("/{project_id}/search")
async def search_nodes(
    project_id: UUID,
    q: str = Query(..., min_length=1, description="Search term"),
    node_type: Optional[str] = Query(default=None, description="Filter by node type"),
    limit: int = Query(
        default=1000, ge=1, le=10000, description="Maximum nodes to return"
    ),
    service: GraphService = Depends(get_graph_service),
):
    """
    Search nodes by name.

    - **project_id**: Project UUID
    - **q**: Search term (matched against node name)
    - **node_type**: Optional node type filter
    - **limit**: Maximum nodes to return (default: 1000, max: 10000)

    Returns nodes matching the search term.
    """
    try:
        nodes = service.search_nodes(project_id, q, node_type, limit)
        return {"nodes": nodes, "total": len(nodes), "query": q, "limit": limit}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching nodes: {e}")
        raise HTTPException(status_code=500, detail="Failed to search nodes")


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: UUID, service: GraphService = Depends(get_graph_service)
):
    """
    Get project statistics.

    - **project_id**: Project UUID

    Returns node and relationship counts.
    """
    try:
        node_count = service.get_node_count(project_id)
        relationship_count = service.get_relationship_count(project_id)

        return {
            "project_id": str(project_id),
            "node_count": node_count,
            "relationship_count": relationship_count,
        }
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/{project_id}/relationships")
async def get_project_relationships(
    project_id: UUID,
    types: Optional[List[str]] = Query(
        default=None,
        description="NOT IMPLEMENTED: Optional relationship type filter. Repeat for multiple types.",
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=100000,
        description="Maximum relationships to return (default: 1000, max: 100000)",
    ),
    service: GraphService = Depends(get_graph_service),
):
    """
    Get all relationships for a project.

    - **project_id**: Project UUID
    - **types**: Optional repeated relationship type filter (e.g. `?types=CONTAINS&types=CALLS`)
    - **limit**: Optional cap on returned records (default: 1000, max: 10000)

    Returns all project-scoped relationships, optionally filtered by type.
    """
    try:
        relationships = service.get_project_relationships(
            project_id=project_id,
            types=types,
            limit=limit,
        )
        return {"relationships": relationships, "total": len(relationships)}
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "Project not found",
                "details": {"project_id": str(project_id)},
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_LIMIT",
                "message": str(e),
                "details": {"parameter": "limit", "minimum": 1, "maximum": 100000},
            },
        )
    except Exception as e:
        logger.error(f"Error retrieving project relationships: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve relationships",
                "details": {"operation": "get_project_relationships"},
            },
        )
