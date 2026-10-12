"""Configuration response models."""
from pydantic import BaseModel
from typing import List


class ConfigDefaultsResponse(BaseModel):
    """Application configuration defaults response."""

    graph_default_visible_nodes: List[str]
    analysis_default_enabled_node_types: List[str]
    enabled_relationship_types: List[str]
    delete_graph_data: bool
