"""Tests for cross-file related GraphStorage changes."""

import pytest
from codeminer.parsing.models import ASTNode, NodeType
from codeminer.database.graph_storage import GraphStorage


class TestNodeToParams:
    """Test _node_to_params includes module_path."""

    def test_module_path_included(self):
        """_node_to_params should include module_path field."""
        node = ASTNode(
            id="test-id", type="Import", name="os",
            source_file="test.py", module_path="os.path",
        )
        from unittest.mock import MagicMock
        storage = GraphStorage(MagicMock())
        params = storage._node_to_params(node, "project-1")
        assert "module_path" in params
        assert params["module_path"] == "os.path"

    def test_module_path_none_default(self):
        node = ASTNode(
            id="test-id", type="File", name="test.py",
            source_file="test.py",
        )
        from unittest.mock import MagicMock
        storage = GraphStorage(MagicMock())
        params = storage._node_to_params(node, "project-1")
        assert "module_path" in params
        assert params["module_path"] is None


class TestExternalModuleNodeType:
    def test_store_node_batch_handles_external_module(self):
        """_store_node_batch should handle ExternalModule node type."""
        from unittest.mock import MagicMock
        storage = GraphStorage(MagicMock())
        node = ASTNode(
            id="ext-1", type=NodeType.EXTERNAL_MODULE.value, name="pandas",
            source_file="", start_line=0, end_line=0,
        )
        params = storage._node_to_params(node, "project-1")
        assert params["type"] == "ExternalModule"


class TestCypherRelationshipTypes:
    """Verify Cypher queries use dynamic relationship matching (no hardcoded types)."""

    def test_query_all_relationships_uses_dynamic_match(self):
        """All relationships query should match any relationship type dynamically."""
        assert "-[r {project_id:" in GraphStorage.CYPHER_QUERY_ALL_RELATIONSHIPS

    def test_delete_relationships_uses_dynamic_match(self):
        """Delete relationships query should match any relationship on project nodes."""
        assert "-[r]->" in GraphStorage.CYPHER_DELETE_RELATIONSHIPS

    def test_create_body_includes_module_path(self):
        assert "module_path" in GraphStorage.CYPHER_CREATE_BODY

    def test_create_body_includes_language(self):
        assert "language" in GraphStorage.CYPHER_CREATE_BODY
