"""Module registry for mapping Python import paths to project files and symbols."""

import os
from dataclasses import dataclass
from logging import getLogger
from typing import Dict, List, Optional

from codeminer.parsing.models import ASTNode, NodeType

logger = getLogger(__name__)

# Common directory prefixes to strip for fallback lookup
_STRIP_PREFIXES = ("src/", "lib/")

# Top-level node types that count as exported symbols (not METHOD — methods are children of classes)
_SYMBOL_TYPES = {NodeType.CLASS.value, NodeType.FUNCTION.value, NodeType.VARIABLE.value}


@dataclass
class ResolvedImport:
    """Result of resolving a single imported name."""
    source_file_node_id: str
    target_file_node_id: Optional[str]
    target_symbol_node_id: Optional[str]
    module_path: str
    imported_name: str
    is_external: bool


class ModuleRegistry:
    """Maps Python dotted module paths to project files and symbols.

    Built from the node list produced by first-pass parsing.
    """

    def __init__(self, nodes: List[ASTNode]) -> None:
        self.module_map: Dict[str, str] = {}   # dotted.path → file_node_id
        self.symbol_map: Dict[str, str] = {}   # dotted.path.Symbol → node_id
        self._file_source_map: Dict[str, str] = {}  # source_file → file_node_id

        self._build(nodes)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, nodes: List[ASTNode]) -> None:
        # Index file nodes
        file_nodes: Dict[str, ASTNode] = {}
        for node in nodes:
            if node.type == NodeType.FILE.value:
                file_nodes[node.source_file] = node
                self._file_source_map[node.source_file] = node.id

        # Register modules
        for source_file, node in file_nodes.items():
            dotted = self._path_to_dotted(source_file)
            self.module_map[dotted] = node.id

            # Fallback with prefix stripping
            for prefix in _STRIP_PREFIXES:
                if source_file.startswith(prefix):
                    stripped = self._path_to_dotted(source_file[len(prefix):])
                    if stripped not in self.module_map:
                        self.module_map[stripped] = node.id

        # Register top-level symbols (children of file nodes)
        for node in nodes:
            if node.type in _SYMBOL_TYPES and node.source_file in file_nodes:
                dotted_file = self._path_to_dotted(node.source_file)
                key = f"{dotted_file}.{node.name}"
                self.symbol_map[key] = node.id

                # Fallback with prefix stripping
                for prefix in _STRIP_PREFIXES:
                    if node.source_file.startswith(prefix):
                        stripped_file = self._path_to_dotted(node.source_file[len(prefix):])
                        stripped_key = f"{stripped_file}.{node.name}"
                        if stripped_key not in self.symbol_map:
                            self.symbol_map[stripped_key] = node.id

    @staticmethod
    def _path_to_dotted(source_file: str) -> str:
        """Convert a file path to a dotted module path.

        mypackage/utils.py       → mypackage.utils
        mypackage/__init__.py    → mypackage
        """
        path = source_file.replace(os.sep, "/")
        if path.endswith("/__init__.py"):
            path = path[: -len("/__init__.py")]
        elif path.endswith(".py"):
            path = path[: -len(".py")]
        return path.replace("/", ".")

    # ------------------------------------------------------------------
    # Resolve
    # ------------------------------------------------------------------

    def resolve(
        self,
        import_module: Optional[str],
        imported_names: List[str],
        source_file: str,
        level: int,
    ) -> List[ResolvedImport]:
        """Resolve an import statement to project files/symbols.

        Args:
            import_module: Dotted module path (None for ``from . import X``)
            imported_names: List of imported names
            source_file: Relative path of the importing file
            level: 0 for absolute, 1+ for relative imports

        Returns:
            List of ResolvedImport, one per imported name.
        """
        # Compute the target module dotted path
        if level > 0:
            base = self._relative_base(source_file, level)
            if import_module:
                target_module = f"{base}.{import_module}" if base else import_module
            else:
                target_module = base
        else:
            target_module = import_module or ""

        # Determine the file node for the target module
        target_file_node_id = self._lookup_module(target_module)

        # Source file node id
        source_file_node_id = self._file_source_map.get(source_file, "")

        results: List[ResolvedImport] = []
        for name in imported_names:
            if name == "*":
                # Star import: file-level only
                results.append(ResolvedImport(
                    source_file_node_id=source_file_node_id,
                    target_file_node_id=target_file_node_id,
                    target_symbol_node_id=None,
                    module_path=target_module,
                    imported_name=name,
                    is_external=target_file_node_id is None,
                ))
                continue

            # Check if the name is the full module path (bare import case)
            if name == target_module:
                results.append(ResolvedImport(
                    source_file_node_id=source_file_node_id,
                    target_file_node_id=target_file_node_id,
                    target_symbol_node_id=None,
                    module_path=target_module,
                    imported_name=name,
                    is_external=target_file_node_id is None,
                ))
                continue

            # Try symbol lookup
            symbol_key = f"{target_module}.{name}"
            symbol_node_id = self.symbol_map.get(symbol_key)

            # If module not found but name might be a sub-module
            if target_file_node_id is None and symbol_node_id is None:
                # Try name as a sub-module of target_module
                sub_module = f"{target_module}.{name}" if target_module else name
                sub_file_node_id = self._lookup_module(sub_module)
                if sub_file_node_id:
                    results.append(ResolvedImport(
                        source_file_node_id=source_file_node_id,
                        target_file_node_id=sub_file_node_id,
                        target_symbol_node_id=None,
                        module_path=sub_module,
                        imported_name=name,
                        is_external=False,
                    ))
                    continue

            if target_file_node_id is None and symbol_node_id is None:
                # External
                results.append(ResolvedImport(
                    source_file_node_id=source_file_node_id,
                    target_file_node_id=None,
                    target_symbol_node_id=None,
                    module_path=target_module,
                    imported_name=name,
                    is_external=True,
                ))
            else:
                results.append(ResolvedImport(
                    source_file_node_id=source_file_node_id,
                    target_file_node_id=target_file_node_id or self._file_for_symbol(symbol_key),
                    target_symbol_node_id=symbol_node_id,
                    module_path=target_module,
                    imported_name=name,
                    is_external=False,
                ))

        return results

    def get_file_node_id(self, source_file: str) -> Optional[str]:
        """Get the file node ID for a given source file path."""
        return self._file_source_map.get(source_file)

    def _lookup_module(self, dotted: str) -> Optional[str]:
        """Look up a module in the map, with prefix-strip fallback."""
        if dotted in self.module_map:
            return self.module_map[dotted]
        return None

    def _file_for_symbol(self, symbol_key: str) -> Optional[str]:
        """Get the file node id for a symbol key by stripping the last segment."""
        parts = symbol_key.rsplit(".", 1)
        if len(parts) == 2:
            return self.module_map.get(parts[0])
        return None

    def _relative_base(self, source_file: str, level: int) -> str:
        """Compute the base module path for a relative import.

        level=1 from mypackage/sub/mod.py → mypackage.sub
        level=2 from mypackage/sub/mod.py → mypackage
        """
        dotted = self._path_to_dotted(source_file)
        parts = dotted.split(".")
        # Drop the filename part
        parts = parts[:-1]
        # Go up `level - 1` more directories
        for _ in range(level - 1):
            if parts:
                parts.pop()
        return ".".join(parts)
