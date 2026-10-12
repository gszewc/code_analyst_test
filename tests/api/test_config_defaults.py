"""API tests for /api/v1/config/defaults endpoint."""
import pytest
from unittest.mock import patch


class TestConfigDefaultsEndpoint:
    """Tests for GET /api/v1/config/defaults."""

    def test_get_config_defaults_returns_200(self, test_client):
        """Endpoint should return 200 OK."""
        response = test_client.get("/api/v1/config/defaults")
        assert response.status_code == 200

    def test_get_config_defaults_response_schema(self, test_client):
        """Response should contain all required fields."""
        response = test_client.get("/api/v1/config/defaults")
        data = response.json()
        assert "graph_default_visible_nodes" in data
        assert "analysis_default_enabled_node_types" in data
        assert "enabled_relationship_types" in data
        assert "delete_graph_data" in data

    def test_get_config_defaults_graph_visible_nodes_is_list(self, test_client):
        """graph_default_visible_nodes should be a list of strings."""
        response = test_client.get("/api/v1/config/defaults")
        data = response.json()
        assert isinstance(data["graph_default_visible_nodes"], list)
        for item in data["graph_default_visible_nodes"]:
            assert isinstance(item, str)

    def test_get_config_defaults_delete_graph_data_is_bool(self, test_client):
        """delete_graph_data should be a boolean."""
        response = test_client.get("/api/v1/config/defaults")
        data = response.json()
        assert isinstance(data["delete_graph_data"], bool)

    def test_get_config_defaults_reflects_env_config(self, test_client):
        """Response should reflect configured graph_default_visible_nodes."""
        from codeminer.config import Settings, get_settings

        custom_settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
            graph_default_visible_nodes="Class,Function",
        )
        with patch("codeminer.api.routes.config.get_settings", return_value=custom_settings):
            response = test_client.get("/api/v1/config/defaults")
        data = response.json()
        assert data["graph_default_visible_nodes"] == ["Class", "Function"]
