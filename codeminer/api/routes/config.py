"""Configuration API routes."""
from fastapi import APIRouter
from ...config import get_settings
from ...models.config import ConfigDefaultsResponse

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/defaults", response_model=ConfigDefaultsResponse)
async def get_config_defaults():
    """Return application configuration defaults."""
    settings = get_settings()
    return ConfigDefaultsResponse(
        graph_default_visible_nodes=settings.graph_default_visible_nodes,
        analysis_default_enabled_node_types=settings.analysis_default_enabled_node_types,
        enabled_relationship_types=settings.analysis_default_enabled_relationship_types,
        delete_graph_data=settings.analysis_default_delete_graph_data,
    )
