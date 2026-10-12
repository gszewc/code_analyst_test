"""Tests for ASTParser component."""

import os
import ast
import pytest
from pathlib import Path

from codeminer.parsing.python.ast_parser import ASTParser
from codeminer.parsing.models import NodeType


class TestASTParser:
    """Test ASTParser functionality."""
    
    def test_parse_simple_file(self, fixtures_dir):
        """Test parsing a simple Python file."""
        parser = ASTParser()
        file_path = os.path.join(fixtures_dir, "sample.py")
        
        result = parser.parse_file(file_path)
        
        assert result.file_info.path == file_path
        assert len(result.nodes) > 0
        assert len(result.errors) == 0
        assert result.summary.total_files == 1
    
    def test_parse_complex_file(self, fixtures_dir):
        """Test parsing a complex Python file with classes."""
        parser = ASTParser()
        file_path = os.path.join(fixtures_dir, "complex.py")
        
        result = parser.parse_file(file_path)
        
        assert result.file_info.path == file_path
        assert len(result.nodes) > 0
        assert len(result.errors) == 0
        
        # Check for class nodes
        class_nodes = [n for n in result.nodes if n.type == 'Class']
        assert len(class_nodes) >= 2  # BaseClass, DerivedClass, DecoratedClass
        
        # Check for method nodes
        method_nodes = [n for n in result.nodes if n.type == 'Method']
        assert len(method_nodes) >= 5
    
    def test_parse_broken_file(self, fixtures_dir):
        """Test parsing a file with syntax errors."""
        parser = ASTParser()
        file_path = os.path.join(fixtures_dir, "broken.py")
        
        result = parser.parse_file(file_path)
        
        assert len(result.errors) > 0
        assert result.summary.total_errors > 0
    
    def test_parse_encoding_error(self, tmp_path):
        """Test parsing a file with encoding issues."""
        parser = ASTParser()
        
        # Create a file with invalid UTF-8
        invalid_file = tmp_path / "invalid.py"
        with open(invalid_file, 'wb') as f:
            f.write(b'\xff\xfe invalid bytes')
        
        result = parser.parse_file(str(invalid_file))
        
        # Should handle gracefully with error
        assert result.summary.total_files == 1
    
    def test_parse_file_not_found(self):
        """Test parsing a non-existent file."""
        parser = ASTParser()
        
        result = parser.parse_file("/nonexistent/path/file.py")
        
        assert len(result.errors) > 0
        assert "File not found" in result.errors[0].message
    
    def test_parse_directory(self, tmp_path):
        """Test parsing a directory of Python files."""
        # Create test files
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("def func2(): pass")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.py").write_text("def func3(): pass")
        
        # Create parser with path validation skipped for testing
        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_directory(str(tmp_path))
        
        assert result.file_info.is_directory is True
        assert result.summary.total_files == 3
        assert len(result.nodes) > 0
    
    def test_parse_source(self):
        """Test parsing source code string."""
        parser = ASTParser()
        source = "def hello(): return 'world'"
        
        tree = parser.parse_source(source, "<test>")
        
        assert tree is not None
        assert isinstance(tree.body[0], ast.FunctionDef)

    def test_parse_file_normalizes_source_file_relative_to_project_root(self, tmp_path):
        """Test source_file values are normalized relative to project root."""
        project_root = tmp_path / "uploads" / "project-1235" / "source"
        project_root.mkdir(parents=True)
        target_file = project_root / "application" / "app.py"
        target_file.parent.mkdir(parents=True)
        target_file.write_text("class App:\n    pass\n", encoding="utf-8")

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_file(str(target_file), project_root=str(project_root))

        assert len(result.errors) == 0
        assert len(result.nodes) > 0
        assert all(node.source_file == "application/app.py" for node in result.nodes)

    def test_parse_file_rejects_out_of_root_path_for_project_normalization(self, tmp_path):
        """Invalid project root should produce parse errors and no persisted nodes."""
        actual_root = tmp_path / "uploads" / "project-1235" / "source"
        wrong_root = tmp_path / "uploads" / "project-9999" / "source"
        actual_root.mkdir(parents=True)
        wrong_root.mkdir(parents=True)

        target_file = actual_root / "application" / "app.py"
        target_file.parent.mkdir(parents=True)
        target_file.write_text("def run():\n    return True\n", encoding="utf-8")

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_file(str(target_file), project_root=str(wrong_root))

        assert len(result.errors) > 0
        assert len(result.nodes) == 0
        assert "Source path normalization failed" in result.errors[0].message


class TestParserRawImports:
    """Verify raw imports flow through parse_file and parse_directory."""

    def test_parse_file_returns_raw_imports(self, tmp_path):
        source_file = tmp_path / "mod.py"
        source_file.write_text("from os import path\nimport sys\n")

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_file(str(source_file))

        assert len(result.raw_imports) == 2

    def test_parse_directory_aggregates_raw_imports(self, tmp_path):
        (tmp_path / "a.py").write_text("import os\n")
        (tmp_path / "b.py").write_text("from sys import argv\n")

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_directory(str(tmp_path))

        assert len(result.raw_imports) == 2

    def test_parse_file_returns_unresolved_references(self, tmp_path):
        source_file = tmp_path / "mod.py"
        source_file.write_text("def foo(): pass\n")

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_file(str(source_file))

        assert isinstance(result.unresolved_references, list)

    def test_raw_imports_collected_when_include_imports_false(self, tmp_path):
        """Critical: raw imports must be collected even with includeImports=False (default)."""
        source_file = tmp_path / "mod.py"
        source_file.write_text("from os.path import join\n")

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_file(str(source_file))

        # includeImports defaults to False in ASTNodeExtractor
        assert len(result.raw_imports) == 1
        import_nodes = [n for n in result.nodes if n.type == "Import"]
        assert len(import_nodes) == 0  # no IMPORT nodes when includeImports=False


# ---------------------------------------------------------------------------
# Alias path tests (US2) — parser preserves project-visible alias source paths
# ---------------------------------------------------------------------------


class TestParserAliasPath:
    """Verify that ASTParser preserves alias paths in parsed node source_file values."""

    def test_parse_file_within_root_uses_relative_path(self, tmp_path):
        root = tmp_path / "source"
        root.mkdir()
        f = root / "app.py"
        f.write_text("def hello(): pass\n")

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_file(str(f), project_root=str(root))

        file_nodes = [n for n in result.nodes if n.type == "File"]
        assert file_nodes, "Expected a File node"
        assert file_nodes[0].source_file == "app.py"

    def test_parse_file_alias_path_through_symlink_preserved(self, tmp_path, require_symlinks):
        """source_file should use the alias path (not realpath) for files reached through symlinks."""
        external = tmp_path / "external"
        external.mkdir()
        (external / "utils.py").write_text("def helper(): pass\n")

        root = tmp_path / "source"
        root.mkdir()
        (root / "lib").symlink_to(external)

        alias_file = root / "lib" / "utils.py"

        parser = ASTParser(skip_path_validation=True)
        result = parser.parse_file(str(alias_file), project_root=str(root))

        assert not result.errors, f"Unexpected errors: {result.errors}"
        file_nodes = [n for n in result.nodes if n.type == "File"]
        assert file_nodes, "Expected a File node"
        assert file_nodes[0].source_file == "lib/utils.py"

    def test_parse_file_two_aliases_same_target_are_distinct(self, tmp_path, require_symlinks):
        """Two alias paths to the same physical file produce distinct source_file values."""
        external = tmp_path / "external"
        external.mkdir()
        (external / "shared.py").write_text("X = 1\n")

        root = tmp_path / "source"
        root.mkdir()
        (root / "alias_a").symlink_to(external)
        (root / "alias_b").symlink_to(external)

        parser = ASTParser(skip_path_validation=True)

        result_a = parser.parse_file(str(root / "alias_a" / "shared.py"), project_root=str(root))
        result_b = parser.parse_file(str(root / "alias_b" / "shared.py"), project_root=str(root))

        file_nodes_a = [n for n in result_a.nodes if n.type == "File"]
        file_nodes_b = [n for n in result_b.nodes if n.type == "File"]

        assert file_nodes_a[0].source_file == "alias_a/shared.py"
        assert file_nodes_b[0].source_file == "alias_b/shared.py"
        assert file_nodes_a[0].source_file != file_nodes_b[0].source_file
