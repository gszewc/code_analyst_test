"""Integration tests for cross-file dependency detection through the full pipeline."""

import os
import pytest
from codeminer.parsing.python.ast_parser import ASTParser
from codeminer.parsing.python.cross_file_resolver import CrossFileResolver
from codeminer.parsing.models import CrossFileConfig, RelationshipType


class TestCrossFilePipeline:
    """Test the full parse → resolve pipeline on a mini multi-file project."""

    @pytest.fixture
    def mini_project(self, tmp_path):
        """Create a mini Python project with cross-file dependencies."""
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        (pkg / "base.py").write_text(
            "class BaseClass:\n"
            "    def base_method(self):\n"
            "        pass\n"
        )

        (pkg / "utils.py").write_text(
            "def helper_func():\n"
            "    return 42\n"
            "\n"
            "GLOBAL_VAR: int = 0\n"
        )

        (pkg / "main.py").write_text(
            "from mypackage.base import BaseClass\n"
            "from mypackage.utils import helper_func\n"
            "\n"
            "class Child(BaseClass):\n"
            "    def do_work(self):\n"
            "        helper_func()\n"
        )

        return tmp_path

    def test_full_pipeline_produces_cross_file_relationships(self, mini_project):
        parser = ASTParser(skip_path_validation=True)
        ast_result = parser.parse_directory(str(mini_project))

        # Verify raw_imports collected
        assert len(ast_result.raw_imports) >= 2

        # Run resolver
        config = CrossFileConfig()
        resolver = CrossFileResolver(config)
        new_rels, new_nodes = resolver.resolve(ast_result)

        # Should have DEPENDS_ON relationships
        depends_on = [r for r in new_rels if r.type == RelationshipType.DEPENDS_ON.value]
        assert len(depends_on) >= 2

        # Should have IMPORTS relationships
        imports = [r for r in new_rels if r.type == RelationshipType.IMPORTS.value]
        assert len(imports) >= 2

        # Should have cross-file EXTENDS
        extends = [r for r in new_rels if r.type == RelationshipType.EXTENDS.value]
        assert len(extends) >= 1

    def test_raw_imports_collected_with_include_imports_false(self, mini_project):
        """Critical: raw imports must be collected even when includeImports=False (default)."""
        parser = ASTParser(skip_path_validation=True)
        ast_result = parser.parse_directory(str(mini_project))

        # Default includeImports=False, but raw_imports must still be populated
        assert len(ast_result.raw_imports) >= 2
        # No IMPORT nodes should exist
        import_nodes = [n for n in ast_result.nodes if n.type == "Import"]
        assert len(import_nodes) == 0

    def test_external_imports_when_enabled(self, mini_project):
        # Add a file with external import
        (mini_project / "mypackage" / "data.py").write_text(
            "import pandas\n"
        )

        parser = ASTParser(skip_path_validation=True)
        ast_result = parser.parse_directory(str(mini_project))

        config = CrossFileConfig(include_external=True)
        resolver = CrossFileResolver(config)
        new_rels, new_nodes = resolver.resolve(ast_result)

        ext_nodes = [n for n in new_nodes if n.type == "ExternalModule"]
        assert len(ext_nodes) >= 1

    def test_config_disables_stages(self, mini_project):
        parser = ASTParser(skip_path_validation=True)
        ast_result = parser.parse_directory(str(mini_project))

        config = CrossFileConfig(imports=False, inheritance=False, calls=False, usage=False)
        resolver = CrossFileResolver(config)
        new_rels, new_nodes = resolver.resolve(ast_result)

        assert len(new_rels) == 0
        assert len(new_nodes) == 0

    def test_summary_recomputation(self, mini_project):
        """After merging cross-file results, summary should reflect new counts."""
        from codeminer.parsing.python.metrics import MetricsCollector
        import time

        parser = ASTParser(skip_path_validation=True)
        ast_result = parser.parse_directory(str(mini_project))

        config = CrossFileConfig()
        resolver = CrossFileResolver(config)
        new_rels, new_nodes = resolver.resolve(ast_result)

        # Merge
        ast_result.nodes.extend(new_nodes)
        ast_result.relationships.extend(new_rels)

        # Recompute summary
        collector = MetricsCollector()
        new_summary = collector.stop(
            time.perf_counter(),
            total_files=ast_result.summary.total_files,
            nodes=ast_result.nodes,
            relationships=ast_result.relationships,
            errors=ast_result.errors,
        )
        ast_result.summary = new_summary

        assert ast_result.summary.total_relationships > 0
        if new_rels:
            assert "DEPENDS_ON" in ast_result.summary.relationships_by_type
