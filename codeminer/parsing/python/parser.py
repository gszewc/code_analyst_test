"""PythonParser — LanguageParser adapter over existing ASTParser."""

from typing import Optional

from codeminer.parsing.interfaces import LanguageParser, CrossFileResolverBase
from codeminer.parsing.models import ASTResult
from codeminer.parsing.types import NodeTypeDefinition, RelationshipTypeDefinition

from .ast_parser import ASTParser
from .cross_file_resolver import PythonCrossFileResolver


class PythonParser(LanguageParser):
    """Adapter wrapping the existing Python AST parser."""

    def __init__(self) -> None:
        self._parser = ASTParser(skip_path_validation=True)

    def get_language_name(self) -> str:
        return "python"

    def get_supported_extensions(self) -> list[str]:
        return [".py"]

    def get_excluded_dirs(self) -> set[str]:
        return {"__pycache__", "venv", ".tox", ".mypy_cache", ".pytest_cache"}

    def get_node_type_definitions(self) -> list[NodeTypeDefinition]:
        lang = "python"
        return [
            NodeTypeDefinition(name="File", language=lang, category="structure", description="Python source file"),
            NodeTypeDefinition(name="Module", language=lang, category="structure", description="Python module"),  # reserved — not currently emitted
            NodeTypeDefinition(name="Package", language=lang, category="structure", description="Python package"),  # reserved — not currently emitted
            NodeTypeDefinition(name="Class", language=lang, category="structure", description="Class definition"),
            NodeTypeDefinition(name="Function", language=lang, category="callable", description="Top-level function"),
            NodeTypeDefinition(name="Method", language=lang, category="callable", description="Class method"),
            NodeTypeDefinition(name="Variable", language=lang, category="data", description="Variable or attribute"),
            NodeTypeDefinition(name="Import", language=lang, category="dependency", description="Import statement"),
            NodeTypeDefinition(name="ExternalModule", language=lang, category="dependency", description="External module reference"),
        ]

    def get_relationship_type_definitions(self) -> list[RelationshipTypeDefinition]:
        lang = "python"
        return [
            RelationshipTypeDefinition(name="CONTAINS", language=lang, category="structural", description="Parent contains child"),
            RelationshipTypeDefinition(name="EXTENDS", language=lang, category="inheritance", description="Class inheritance"),
            RelationshipTypeDefinition(name="IMPLEMENTS", language=lang, category="inheritance", description="Interface implementation"),  # reserved — not currently emitted; see nodes_visitor.py:509
            RelationshipTypeDefinition(name="CALLS", language=lang, category="usage", description="Function/method call"),
            RelationshipTypeDefinition(name="DEPENDS_ON", language=lang, category="dependency", description="File-level dependency"),
            RelationshipTypeDefinition(name="USES", language=lang, category="usage", description="Variable/attribute usage"),
            RelationshipTypeDefinition(name="IMPORTS", language=lang, category="dependency", description="Import relationship"),
        ]

    def parse_file(self, file_path: str, project_root: Optional[str] = None) -> ASTResult:
        result = self._parser.parse_file(file_path, project_root)
        self._set_language(result)
        return result

    def parse_files(self, file_paths: list[str], project_root: Optional[str] = None) -> ASTResult:
        if not file_paths:
            return ASTResult()
        from .metrics import MetricsCollector
        import time

        start_time = time.perf_counter()
        all_nodes = []
        all_relationships = []
        all_errors = []
        all_raw_imports = []
        all_unresolved_refs = []

        for fp in file_paths:
            r = self._parser.parse_file(fp, project_root)
            all_nodes.extend(r.nodes)
            all_relationships.extend(r.relationships)
            all_errors.extend(r.errors)
            all_raw_imports.extend(r.raw_imports)
            all_unresolved_refs.extend(r.unresolved_references)

        collector = MetricsCollector()
        summary = collector.stop(
            start_time,
            total_files=len(file_paths),
            nodes=all_nodes,
            relationships=all_relationships,
            errors=all_errors,
        )

        result = ASTResult(
            file_info=None,
            nodes=all_nodes,
            relationships=all_relationships,
            errors=all_errors,
            summary=summary,
            raw_imports=all_raw_imports,
            unresolved_references=all_unresolved_refs,
        )
        self._set_language(result)
        return result

    def create_cross_file_resolver(self) -> Optional[CrossFileResolverBase]:
        return PythonCrossFileResolver()

    @staticmethod
    def _set_language(result: ASTResult) -> None:
        """Set language='python' on all nodes in the result."""
        for node in result.nodes:
            node.language = "python"
