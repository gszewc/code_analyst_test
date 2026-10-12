"""Repository map generator — produces aider-style repomap.txt from AST nodes."""

import logging
from collections import defaultdict
from pathlib import Path
from typing import List

from ..parsing.models import ASTNode

logger = logging.getLogger(__name__)

_MAP_TYPES = {"Class", "Interface", "Enum", "Function", "Method", "Variable"}


class RepoMapGenerator:
    """Generate an aider-style repository map from AST nodes.

    Format:
        path/to/file.py:
        │class MyClass:
        │    def method(self):
        │def top_func():

    Language-agnostic: driven entirely by ASTNode.signature.
    Nodes with no signature are silently skipped.
    """

    def generate(self, nodes: List[ASTNode], output_path: Path) -> None:
        """Render nodes as aider-style text and write to output_path.

        Errors writing the file are logged and swallowed — map generation
        must never fail an analysis job.
        """
        content = self._render(nodes)
        try:
            output_path.write_text(content, encoding="utf-8")
            logger.info(f"Repository map written to {output_path}")
        except OSError as e:
            logger.error(f"Failed to write repository map to {output_path}: {e}")

    def _render(self, nodes: List[ASTNode]) -> str:
        """Render all nodes as aider-style text."""
        relevant = [n for n in nodes if n.type in _MAP_TYPES and n.source_file]

        if not relevant:
            return "# Repository map (no nodes found)\n"

        by_file: dict[str, list[ASTNode]] = defaultdict(list)
        for node in relevant:
            by_file[node.source_file].append(node)

        lines: list[str] = []
        for file_path in sorted(by_file.keys()):
            file_nodes = sorted(by_file[file_path], key=lambda n: n.start_line)
            file_lines = self._render_file(file_nodes)
            if file_lines:
                lines.append(f"{file_path}:")
                lines.extend(file_lines)
                lines.append("")  # blank line after each file block

        if not lines:
            return "# Repository map (no nodes found)\n"

        return "\n".join(lines)

    def _render_file(self, nodes: List[ASTNode]) -> list[str]:
        """Render nodes for one file, respecting class membership."""
        class_ranges = [
            (n.start_line, n.end_line)
            for n in nodes
            if n.type == "Class" and n.signature
        ]

        lines: list[str] = []
        for node in nodes:
            if not node.signature:
                continue

            inside_class = node.type != "Class" and any(
                start <= node.start_line <= end for start, end in class_ranges
            )
            indent = "    " if inside_class else ""

            if node.decorators:
                for dec in node.decorators:
                    lines.append(f"│{indent}@{dec}")

            for sig_line in node.signature.splitlines():
                lines.append(f"│{indent}{sig_line}")

        return lines
