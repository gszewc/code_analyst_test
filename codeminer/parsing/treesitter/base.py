"""Tree-sitter base class for language parsers."""

import os
import time
import uuid
from abc import abstractmethod
from logging import getLogger
from typing import Any

import tree_sitter

from codeminer.parsing.interfaces import LanguageParser
from codeminer.parsing.metrics import MetricsCollector
from codeminer.parsing.models import (
    ASTNode,
    ASTResult,
    FileInfo,
    ParseError,
    Relationship,
)

logger = getLogger(__name__)


class TreeSitterLanguageParser(LanguageParser):
    """Base class for tree-sitter-backed language parsers.

    Handles tree-sitter boilerplate: grammar loading, file parsing,
    S-expression query execution, metrics collection.
    Subclasses define language-specific queries and node mapping.
    """

    def __init__(self) -> None:
        ts_language = self._load_language()
        self._language = tree_sitter.Language(ts_language)
        self._parser = tree_sitter.Parser(self._language)
        # NOTE: _pending_raw_imports and _current_file_node_id are per-file state.
        # JavaParser resets both at the start of each parse_file() call.
        # This is safe in single-threaded use, but NOT thread-safe when the parser
        # is used as a singleton under concurrent requests. If concurrency is needed,
        # these should be refactored into parse_file() local variables.
        self._pending_raw_imports: list = []
        self._current_file_node_id: str = ""

    @abstractmethod
    def _load_language(self) -> Any:
        """Return the tree-sitter language object (e.g. tree_sitter_java.language())."""

    @abstractmethod
    def _get_node_queries(self) -> dict[str, str]:
        """S-expression queries keyed by node type name.

        Each query MUST have two captures: @name (identifier) and @node (full node).
        Example: {"Class": "(class_declaration name: (identifier) @name) @node"}
        """

    @abstractmethod
    def _map_node(
        self,
        ts_node,
        node_type: str,
        name: str,
        source_file: str,
        project_root: str | None,
    ) -> ASTNode:
        """Convert a tree-sitter node capture to an ASTNode."""

    @abstractmethod
    def _extract_intra_file_relationships(
        self, nodes: list[ASTNode], tree
    ) -> list[Relationship]:
        """Return intra-file relationships (e.g. CONTAINS) from the node list."""

    def parse_file(self, file_path: str, project_root: str | None = None) -> ASTResult:
        """Parse a single file and return its AST result."""
        try:
            source_bytes = self._read_file(file_path)
            tree = self._parser.parse(source_bytes)

            # Create File node
            file_name = os.path.basename(file_path)
            rel_path = (
                os.path.relpath(file_path, project_root) if project_root else file_path
            )
            file_node = ASTNode(
                id=str(uuid.uuid4()),
                type="File",
                name=file_name,
                source_file=rel_path,
                start_line=1,
                end_line=tree.root_node.end_point[0] + 1,
                start_column=0,
                end_column=0,
            )

            # Extract nodes via queries
            query_nodes = self._extract_nodes(tree, rel_path, project_root)
            all_nodes = [file_node] + query_nodes

            # Extract intra-file relationships
            relationships = self._extract_intra_file_relationships(all_nodes, tree)

            # Collect raw imports (subclass populates via _map_node side-effects)
            raw_imports = list(getattr(self, "_pending_raw_imports", []))
            self._pending_raw_imports = []

            # Set language on all nodes
            lang = self.get_language_name()
            for node in all_nodes:
                node.language = lang

            file_size = os.path.getsize(file_path)
            return ASTResult(
                file_info=FileInfo(
                    path=file_path,
                    name=file_name,
                    size=file_size,
                    language=lang,
                ),
                nodes=all_nodes,
                relationships=relationships,
                raw_imports=raw_imports,
            )

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return ASTResult(errors=[ParseError(file_path=file_path, message=str(e))])

    def parse_files(
        self, file_paths: list[str], project_root: str | None = None
    ) -> ASTResult:
        """Parse multiple files, merging results."""
        if not file_paths:
            return ASTResult()

        start_time = time.perf_counter()
        all_nodes: list[ASTNode] = []
        all_relationships: list[Relationship] = []
        all_errors = []
        all_raw_imports = []
        all_unresolved_refs = []

        for fp in file_paths:
            r = self.parse_file(fp, project_root)
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

        return ASTResult(
            file_info=None,
            nodes=all_nodes,
            relationships=all_relationships,
            errors=all_errors,
            summary=summary,
            raw_imports=all_raw_imports,
            unresolved_references=all_unresolved_refs,
        )

    def _extract_nodes(
        self, tree, source_file: str, project_root: str | None
    ) -> list[ASTNode]:
        """Run all S-expression queries and return extracted ASTNodes."""
        nodes: list[ASTNode] = []
        queries = self._get_node_queries()

        for node_type, query_str in queries.items():
            try:
                query = tree_sitter.Query(self._language, query_str)
                cursor = tree_sitter.QueryCursor(query)
                captures = cursor.captures(tree.root_node)

                # captures is dict[str, list[Node]]
                name_nodes = captures.get("name", [])
                full_nodes = captures.get("node", [])

                if len(name_nodes) != len(full_nodes):
                    logger.warning(
                        "Query '%s' capture count mismatch: %d name captures vs %d node captures — skipping",
                        node_type,
                        len(name_nodes),
                        len(full_nodes),
                    )
                    continue

                for name_node, full_node in zip(name_nodes, full_nodes):
                    name_text = (
                        name_node.text.decode("utf-8")
                        if isinstance(name_node.text, bytes)
                        else str(name_node.text)
                    )
                    ast_node = self._map_node(
                        full_node, node_type, name_text, source_file, project_root
                    )
                    nodes.append(ast_node)

            except Exception as e:
                logger.warning(f"Query failed for {node_type} in {source_file}: {e}")

        return nodes

    @staticmethod
    def _read_file(file_path: str) -> bytes:
        """Read a file as bytes."""
        with open(file_path, "rb") as f:
            return f.read()
