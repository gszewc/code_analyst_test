"""Tests for AnalysisDefaults configuration."""

import os
import tempfile
from codeminer.config import Settings


class TestAnalysisDefaults:
    """Test analysis default configuration."""

    def test_defaults_all_types_enabled(self):
        """Factory defaults should enable all node and relationship types."""
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
        )
        defaults = settings.analysis_defaults
        assert defaults.delete_graph_data is False
        assert len(defaults.enabled_node_types) == 12
        assert "File" in defaults.enabled_node_types
        assert "Interface" in defaults.enabled_node_types
        assert "Enum" in defaults.enabled_node_types
        assert "Constructor" in defaults.enabled_node_types
        assert "ExternalModule" in defaults.enabled_node_types
        assert len(defaults.enabled_relationship_types) == 7
        assert "CONTAINS" in defaults.enabled_relationship_types

    def test_defaults_comma_separated_parsing(self):
        """Comma-separated env values should parse into lists."""
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
            analysis_default_enabled_node_types="File,Class,Function",
            analysis_default_enabled_relationship_types="CONTAINS,CALLS",
        )
        defaults = settings.analysis_defaults
        assert defaults.enabled_node_types == ["File", "Class", "Function"]
        assert defaults.enabled_relationship_types == ["CONTAINS", "CALLS"]

    def test_defaults_delete_graph_data_from_env(self):
        """Delete flag should be configurable via env."""
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
            analysis_default_delete_graph_data=True,
        )
        assert settings.analysis_defaults.delete_graph_data is True


class TestGraphDefaultVisibleNodes:
    """Test graph_default_visible_nodes configuration."""

    def test_graph_defaults_default_value(self, monkeypatch):
        """Factory default should include Class, Interface, Enum, Function, Method."""
        monkeypatch.delenv("GRAPH_DEFAULT_VISIBLE_NODES", raising=False)
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
        )
        defaults = settings.graph_default_visible_nodes
        assert isinstance(defaults, list)
        assert "Class" in defaults
        assert "Interface" in defaults
        assert "Function" in defaults
        assert "Method" in defaults
        assert "Enum" in defaults

    def test_graph_defaults_comma_separated_parsing(self):
        """Comma-separated env string should parse into list."""
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
            graph_default_visible_nodes="Class,Method,Function",
        )
        assert settings.graph_default_visible_nodes == ["Class", "Method", "Function"]

    def test_graph_defaults_unknown_types_filtered(self):
        """Unknown node types should be filtered out silently."""
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
            graph_default_visible_nodes="Class,NotAType,Function",
        )
        assert "Class" in settings.graph_default_visible_nodes
        assert "Function" in settings.graph_default_visible_nodes
        assert "NotAType" not in settings.graph_default_visible_nodes

    def test_graph_defaults_empty_config(self):
        """Empty GRAPH_DEFAULT_VISIBLE_NODES should result in empty list."""
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
            graph_default_visible_nodes="",
        )
        assert settings.graph_default_visible_nodes == []

    def test_graph_defaults_duplicate_types_normalized(self):
        """Duplicate types should be deduplicated."""
        settings = Settings(
            _env_file=None,
            neo4j_uri="bolt://localhost:7687",
            graph_default_visible_nodes="Class,Class,Function",
        )
        assert settings.graph_default_visible_nodes.count("Class") == 1
        assert "Function" in settings.graph_default_visible_nodes

    def test_graph_defaults_from_env_var(self, monkeypatch):
        """CSV value from an actual env var should parse without SettingsError."""
        monkeypatch.setenv("GRAPH_DEFAULT_VISIBLE_NODES", "Package,Class")
        settings = Settings(_env_file=None, neo4j_uri="bolt://localhost:7687")
        assert settings.graph_default_visible_nodes == ["Package", "Class"]

    def test_graph_defaults_from_env_var_with_spaces(self, monkeypatch):
        """Spaces around node type names should be stripped."""
        monkeypatch.setenv("GRAPH_DEFAULT_VISIBLE_NODES", " Package , Class ")
        settings = Settings(_env_file=None, neo4j_uri="bolt://localhost:7687")
        assert settings.graph_default_visible_nodes == ["Package", "Class"]

    def test_graph_defaults_from_dotenv_file(self):
        """CSV value in a .env file should parse without SettingsError."""
        content = "NEO4J_URI=bolt://localhost:7687\nGRAPH_DEFAULT_VISIBLE_NODES=Package,Class\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            settings = Settings(_env_file=tmp_path)
            assert settings.graph_default_visible_nodes == ["Package", "Class"]
        finally:
            os.unlink(tmp_path)

    def test_graph_defaults_json_array_format_still_works(self, monkeypatch):
        """JSON array format should still be accepted alongside CSV."""
        monkeypatch.setenv("GRAPH_DEFAULT_VISIBLE_NODES", '["Package","Class"]')
        settings = Settings(_env_file=None, neo4j_uri="bolt://localhost:7687")
        assert settings.graph_default_visible_nodes == ["Package", "Class"]
