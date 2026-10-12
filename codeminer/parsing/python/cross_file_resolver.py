"""Cross-file relationship resolver.

Runs after first-pass parsing to detect relationships between files:
- Stage 1: Build registry and indexes
- Stage 2: Resolve imports (DEPENDS_ON, IMPORTS)
- Stage 3: Resolve cross-file inheritance (EXTENDS)
- Stage 4: Resolve cross-file calls and usage (CALLS, USES)
"""

import uuid
from logging import getLogger
from typing import Dict, List, Optional, Set, Tuple

from codeminer.parsing.interfaces import CrossFileResolverBase
from codeminer.parsing.models import (
    ASTNode, ASTResult, Relationship, RelationshipType, NodeType,
    CrossFileConfig, RawImport, UnresolvedReference,
)
from .module_registry import ModuleRegistry

logger = getLogger(__name__)


class PythonCrossFileResolver(CrossFileResolverBase):
    """Detects cross-file relationships from raw import data and unresolved references."""

    def __init__(self, config: Optional[CrossFileConfig] = None) -> None:
        self.config = config or CrossFileConfig()  # default, overridden in resolve()

    def resolve(
        self, ast_result: ASTResult, config=None
    ) -> Tuple[List[Relationship], List[ASTNode]]:
        """Run all resolution stages.

        Args:
            ast_result: Complete first-pass parsing result.
            config: Optional cross-file config flags.

        Returns:
            Tuple of (new_relationships, new_nodes).
        """
        if config is not None:
            self.config = config
        new_relationships: List[Relationship] = []
        new_nodes: List[ASTNode] = []

        # Stage 1: Build registry and indexes
        registry = ModuleRegistry(ast_result.nodes)
        node_index: Dict[str, ASTNode] = {n.id: n for n in ast_result.nodes}

        # Import alias index: (file_node_id, local_name) → fully_qualified_symbol_key
        import_alias_index: Dict[Tuple[str, str], str] = {}

        # Stage 2: Resolve imports (always runs to populate alias index)
        seen_depends_on: Set[Tuple[str, str]] = set()
        external_modules: Dict[str, ASTNode] = {}  # module_path → node

        try:
            for raw_import in ast_result.raw_imports:
                resolved_list = registry.resolve(
                    raw_import.module, raw_import.names,
                    raw_import.source_file, raw_import.level,
                )

                for resolved in resolved_list:
                    # Populate alias index
                    if resolved.target_symbol_node_id and not resolved.is_external:
                        local_name = resolved.imported_name
                        fq_key = f"{resolved.module_path}.{resolved.imported_name}"
                        import_alias_index[(raw_import.source_file_node_id, local_name)] = fq_key

                    if resolved.is_external:
                        if self.config.include_external:
                            # Create or reuse EXTERNAL_MODULE node
                            if resolved.module_path not in external_modules:
                                ext_node = ASTNode(
                                    id=str(uuid.uuid4()),
                                    type=NodeType.EXTERNAL_MODULE.value,
                                    name=resolved.module_path,
                                    source_file="",
                                    start_line=0, end_line=0,
                                    start_column=0, end_column=0,
                                )
                                external_modules[resolved.module_path] = ext_node
                                new_nodes.append(ext_node)

                            if self.config.imports:
                                ext_node = external_modules[resolved.module_path]
                                dep_key = (resolved.source_file_node_id, ext_node.id)
                                if dep_key not in seen_depends_on:
                                    seen_depends_on.add(dep_key)
                                    new_relationships.append(Relationship(
                                        source_id=resolved.source_file_node_id,
                                        target_id=ext_node.id,
                                        type=RelationshipType.DEPENDS_ON.value,
                                    ))
                        continue

                    if self.config.imports:
                        # DEPENDS_ON (file → file), deduplicated
                        if resolved.target_file_node_id:
                            dep_key = (resolved.source_file_node_id, resolved.target_file_node_id)
                            if dep_key not in seen_depends_on:
                                seen_depends_on.add(dep_key)
                                new_relationships.append(Relationship(
                                    source_id=resolved.source_file_node_id,
                                    target_id=resolved.target_file_node_id,
                                    type=RelationshipType.DEPENDS_ON.value,
                                ))

                        # IMPORTS (file → symbol)
                        if resolved.target_symbol_node_id and resolved.imported_name != "*":
                            new_relationships.append(Relationship(
                                source_id=resolved.source_file_node_id,
                                target_id=resolved.target_symbol_node_id,
                                type=RelationshipType.IMPORTS.value,
                            ))
        except Exception:
            logger.exception("Stage 2 (import resolution) failed")

        # Stage 3: Resolve cross-file inheritance
        try:
            if self.config.inheritance:
                for node in ast_result.nodes:
                    if node.type == NodeType.CLASS.value and node.base_classes:
                        file_node_id = registry.get_file_node_id(node.source_file)
                        if not file_node_id:
                            continue
                        for base_name in node.base_classes:
                            # Check if already resolved within same file (skip)
                            if self._is_same_file_class(base_name, node.source_file, ast_result.nodes):
                                continue
                            # Look up in alias index
                            alias_key = (file_node_id, base_name)
                            fq_key = import_alias_index.get(alias_key)
                            if fq_key:
                                target_id = registry.symbol_map.get(fq_key)
                                if target_id:
                                    new_relationships.append(Relationship(
                                        source_id=node.id,
                                        target_id=target_id,
                                        type=RelationshipType.EXTENDS.value,
                                    ))
        except Exception:
            logger.exception("Stage 3 (inheritance resolution) failed")

        # Stage 4: Resolve cross-file calls and usage
        try:
            for ref in ast_result.unresolved_references:
                if ref.reference_type == "call" and not self.config.calls:
                    continue
                if ref.reference_type == "usage" and not self.config.usage:
                    continue

                file_node_id = registry.get_file_node_id(ref.source_file)
                if not file_node_id:
                    continue

                parts = ref.reference_name.split(".", 1)
                object_name = parts[0]
                attribute = parts[1] if len(parts) > 1 else None

                alias_key = (file_node_id, object_name)
                fq_key = import_alias_index.get(alias_key)
                if not fq_key:
                    continue

                if attribute:
                    # Dotted reference: find the attribute in children of resolved node
                    target_class_id = registry.symbol_map.get(fq_key)
                    if target_class_id:
                        target_method = self._find_child(
                            target_class_id, attribute, ast_result.relationships, node_index,
                        )
                        if target_method:
                            rel_type = (
                                RelationshipType.CALLS.value
                                if ref.reference_type == "call"
                                else RelationshipType.USES.value
                            )
                            new_relationships.append(Relationship(
                                source_id=ref.source_node_id,
                                target_id=target_method,
                                type=rel_type,
                            ))
                else:
                    # Simple reference
                    target_id = registry.symbol_map.get(fq_key)
                    if target_id:
                        rel_type = (
                            RelationshipType.CALLS.value
                            if ref.reference_type == "call"
                            else RelationshipType.USES.value
                        )
                        new_relationships.append(Relationship(
                            source_id=ref.source_node_id,
                            target_id=target_id,
                            type=rel_type,
                        ))
        except Exception:
            logger.exception("Stage 4 (call/usage resolution) failed")

        return new_relationships, new_nodes

    @staticmethod
    def _is_same_file_class(class_name: str, source_file: str, nodes: List[ASTNode]) -> bool:
        """Check if a class name exists in the same file."""
        return any(
            n.type == NodeType.CLASS.value
            and n.name == class_name
            and n.source_file == source_file
            for n in nodes
        )

    @staticmethod
    def _find_child(
        parent_id: str,
        child_name: str,
        relationships: List[Relationship],
        node_index: Dict[str, ASTNode],
    ) -> Optional[str]:
        """Find a child node by name in CONTAINS relationships."""
        for rel in relationships:
            if rel.source_id == parent_id and rel.type == RelationshipType.CONTAINS.value:
                child = node_index.get(rel.target_id)
                if child and child.name == child_name:
                    return child.id
        return None


# Backward-compatibility alias
CrossFileResolver = PythonCrossFileResolver
