"""Tests for TreeSitterLanguageParser base class."""

import uuid


import tree_sitter_java
from tree_sitter import Language

from codeminer.parsing.treesitter.base import TreeSitterLanguageParser
from codeminer.parsing.models import ASTNode, ASTResult, Relationship
from codeminer.parsing.types import NodeTypeDefinition, RelationshipTypeDefinition


class _StubParser(TreeSitterLanguageParser):
    """Minimal concrete subclass for testing the base class."""

    def _load_language(self) -> Language:
        return tree_sitter_java.language()

    def get_language_name(self) -> str:
        return "java"

    def get_supported_extensions(self) -> list[str]:
        return [".java"]

    def get_excluded_dirs(self) -> set[str]:
        return {"build"}

    def get_node_type_definitions(self) -> list[NodeTypeDefinition]:
        return []

    def get_relationship_type_definitions(self) -> list[RelationshipTypeDefinition]:
        return []

    def _get_node_queries(self) -> dict[str, str]:
        return {
            "Class": "(class_declaration name: (identifier) @name) @node",
        }

    def _map_node(
        self,
        ts_node,
        node_type: str,
        name: str,
        source_file: str,
        project_root: str | None,
    ) -> ASTNode:
        return ASTNode(
            id=str(uuid.uuid4()),
            type=node_type,
            name=name,
            source_file=source_file,
            start_line=ts_node.start_point[0] + 1,
            end_line=ts_node.end_point[0] + 1,
            start_column=ts_node.start_point[1],
            end_column=ts_node.end_point[1],
        )

    def _extract_intra_file_relationships(
        self, nodes: list[ASTNode], tree
    ) -> list[Relationship]:
        return []

    def create_cross_file_resolver(self):
        return None


class TestTreeSitterLanguageParser:
    """Tests for TreeSitterLanguageParser base class."""

    def test_parse_file_extracts_nodes(self, tmp_path):
        """parse_file returns ASTResult with nodes extracted by queries."""
        java_file = tmp_path / "Hello.java"
        java_file.write_text("public class Hello { }")

        parser = _StubParser()
        result = parser.parse_file(str(java_file), str(tmp_path))

        assert isinstance(result, ASTResult)
        class_nodes = [n for n in result.nodes if n.type == "Class"]
        assert len(class_nodes) == 1
        assert class_nodes[0].name == "Hello"

    def test_parse_file_creates_file_node(self, tmp_path):
        """parse_file creates a File node for the file."""
        java_file = tmp_path / "Foo.java"
        java_file.write_text("public class Foo { }")

        parser = _StubParser()
        result = parser.parse_file(str(java_file), str(tmp_path))

        file_nodes = [n for n in result.nodes if n.type == "File"]
        assert len(file_nodes) == 1
        assert file_nodes[0].name == "Foo.java"

    def test_parse_file_sets_language(self, tmp_path):
        """parse_file sets language on all nodes."""
        java_file = tmp_path / "Hello.java"
        java_file.write_text("public class Hello { }")

        parser = _StubParser()
        result = parser.parse_file(str(java_file), str(tmp_path))

        for node in result.nodes:
            assert node.language == "java"

    def test_parse_file_error_recovery(self):
        """parse_file returns ASTResult with error for non-existent file."""
        parser = _StubParser()
        result = parser.parse_file("/nonexistent/Foo.java", "/nonexistent")

        assert isinstance(result, ASTResult)
        assert len(result.errors) == 1
        assert result.nodes == []

    def test_parse_files_merges_results(self, tmp_path):
        """parse_files merges nodes from multiple files."""
        (tmp_path / "A.java").write_text("public class A { }")
        (tmp_path / "B.java").write_text("public class B { }")

        parser = _StubParser()
        result = parser.parse_files(
            [str(tmp_path / "A.java"), str(tmp_path / "B.java")],
            str(tmp_path),
        )

        class_nodes = [n for n in result.nodes if n.type == "Class"]
        assert len(class_nodes) == 2
        names = {n.name for n in class_nodes}
        assert names == {"A", "B"}
        assert result.summary.total_files == 2

    def test_parse_files_empty_list(self):
        """parse_files with empty list returns empty ASTResult."""
        parser = _StubParser()
        result = parser.parse_files([], None)

        assert isinstance(result, ASTResult)
        assert result.nodes == []

    def test_parse_file_line_numbers(self, tmp_path):
        """parse_file extracts correct line numbers (1-indexed)."""
        java_file = tmp_path / "Lines.java"
        java_file.write_text("// comment\npublic class Lines {\n}\n")

        parser = _StubParser()
        result = parser.parse_file(str(java_file), str(tmp_path))

        class_nodes = [n for n in result.nodes if n.type == "Class"]
        assert len(class_nodes) == 1
        assert class_nodes[0].start_line == 2
        assert class_nodes[0].end_line == 3
