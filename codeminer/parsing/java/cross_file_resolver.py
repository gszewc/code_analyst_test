"""Java cross-file relationship resolver.

Resolves:
- Stage 1: Build indexes (class → node, FQN → node, file → File node)
- Stage 2: Imports → DEPENDS_ON + IMPORTS relationships
- Stage 3: Inheritance → EXTENDS + IMPLEMENTS relationships
- Stage 4: Package containment → Package→CONTAINS→Class/Interface relationships
"""

import os
import uuid
from logging import getLogger
from typing import Optional

from codeminer.parsing.interfaces import CrossFileResolverBase
from codeminer.parsing.models import ASTNode, ASTResult, CrossFileConfig, Relationship

logger = getLogger(__name__)


class JavaCrossFileResolver(CrossFileResolverBase):
    """Resolves cross-file relationships for Java: imports + inheritance."""

    def resolve(
        self,
        ast_result: ASTResult,
        config: Optional[CrossFileConfig] = None,
    ) -> tuple[list[Relationship], list[ASTNode]]:
        """Resolve cross-file relationships.

        Args:
            ast_result: Combined ASTResult for all Java files.
            config: Optional config flags (unused for now).

        Returns:
            Tuple of (new_relationships, new_nodes).
        """
        new_relationships: list[Relationship] = []
        new_nodes: list[ASTNode] = []

        # Stage 1: Build indexes
        class_index: dict[str, ASTNode] = {}  # simple name → node
        fqn_index: dict[str, ASTNode] = {}  # fqn → node
        iface_names: set[str] = set()  # track which names are interfaces
        file_node_index: dict[str, ASTNode] = {}  # source_file → File node
        package_index: dict[str, str] = {}  # source_file → package name

        same_file_class_keys: set[tuple[str, str]] = set()

        # Pass 1: Build a directory-level mapping from Package nodes so we can
        # cover source files whose Package node was removed by canonicalization.
        # JavaParser._canonicalize_package_nodes() keeps only ONE Package node per
        # module_path (the first encountered file).  Other files in the same package
        # (e.g. Dog.java when Animal.java's Package node is canonical) have no Package
        # node left, so a naive source_file lookup would miss them.  Because all Java
        # files in the same directory belong to the same package, we derive
        # source_file → module_path for those missing files via directory matching.
        pkg_dir_index: dict[str, str] = {}  # directory → module_path
        for node in ast_result.nodes:
            if node.type == "Package" and node.module_path:
                pkg_dir = os.path.dirname(node.source_file)
                pkg_dir_index[pkg_dir] = node.module_path
                # Also record the Package node's own source_file directly so that
                # unit tests without File nodes (e.g. tests using only Package + Class
                # nodes in-memory) still resolve correctly.
                package_index[node.source_file] = node.module_path

        # Pass 2: Build remaining indexes; extend package_index for File nodes.
        for node in ast_result.nodes:
            if node.type == "File":
                file_node_index[node.source_file] = node
                # Extend package_index to cover all source files via directory match.
                if node.source_file not in package_index:
                    file_dir = os.path.dirname(node.source_file)
                    if file_dir in pkg_dir_index:
                        package_index[node.source_file] = pkg_dir_index[file_dir]
            elif node.type == "Class":
                class_index[node.name] = node
                same_file_class_keys.add((node.name, node.source_file))
            elif node.type == "Interface":
                class_index[node.name] = node
                iface_names.add(node.name)
                same_file_class_keys.add((node.name, node.source_file))
            elif node.type == "Enum":
                class_index[node.name] = node
                same_file_class_keys.add((node.name, node.source_file))

        # Build FQN index: package + class name
        for node in ast_result.nodes:
            if node.type in ("Class", "Interface", "Enum"):
                pkg = package_index.get(node.source_file)
                if pkg:
                    fqn = f"{pkg}.{node.name}"
                    fqn_index[fqn] = node

        # Stage 2: Resolve imports → DEPENDS_ON + IMPORTS
        seen_depends_on: set[tuple[str, str]] = set()
        external_modules: dict[str, ASTNode] = {}

        for raw_import in ast_result.raw_imports:
            try:
                source_file_node = file_node_index.get(raw_import.source_file)
                if source_file_node:
                    source_node_id = source_file_node.id
                else:
                    # Fall back to source_file_node_id from the raw import
                    source_node_id = raw_import.source_file_node_id

                # Look up target: try FQN first, then simple name derived from module
                target_node = (
                    fqn_index.get(raw_import.module) if raw_import.module else None
                )
                if not target_node:
                    simple_name = raw_import.module.rsplit(".", 1)[-1]
                    target_node = class_index.get(simple_name)

                if target_node:
                    # Internal import
                    new_relationships.append(
                        Relationship(
                            source_id=source_node_id,
                            target_id=target_node.id,
                            type="IMPORTS",
                        )
                    )

                    # DEPENDS_ON (file → file), deduplicated
                    target_file_node = file_node_index.get(target_node.source_file)
                    if target_file_node:
                        dep_key = (source_node_id, target_file_node.id)
                        if dep_key not in seen_depends_on:
                            seen_depends_on.add(dep_key)
                            new_relationships.append(
                                Relationship(
                                    source_id=source_node_id,
                                    target_id=target_file_node.id,
                                    type="DEPENDS_ON",
                                )
                            )
                else:
                    # External import — synthesise ExternalModule
                    module_path = raw_import.module or (
                        raw_import.names[0] if raw_import.names else ""
                    )
                    if not module_path:
                        continue
                    if module_path not in external_modules:
                        ext_node = ASTNode(
                            id=str(uuid.uuid4()),
                            type="ExternalModule",
                            name=module_path,
                            source_file="",
                            start_line=0,
                            end_line=0,
                            language="java",
                            module_path=module_path,
                        )
                        external_modules[module_path] = ext_node
                        new_nodes.append(ext_node)

                    ext_node = external_modules[module_path]
                    new_relationships.append(
                        Relationship(
                            source_id=source_node_id,
                            target_id=ext_node.id,
                            type="IMPORTS",
                        )
                    )
            except Exception as e:
                logger.warning(
                    "Failed to resolve import '%s': %s",
                    raw_import.module,
                    e,
                    exc_info=True,
                )

        # Stage 3: Resolve inheritance → EXTENDS + IMPLEMENTS
        for node in ast_result.nodes:
            if node.type not in ("Class", "Interface", "Enum"):
                continue
            if not node.base_classes:
                continue

            for base_name in node.base_classes:
                try:
                    # Skip same-file classes (already handled by intra-file)
                    if (base_name, node.source_file) in same_file_class_keys:
                        continue

                    target = class_index.get(base_name)
                    if not target:
                        # Try FQN lookup with all known packages
                        for pkg in package_index.values():
                            fqn = f"{pkg}.{base_name}"
                            target = fqn_index.get(fqn)
                            if target:
                                break

                    if not target:
                        continue  # External base class — skip

                    # Determine relationship type.
                    # Interface-extends-interface is EXTENDS in Java; only a
                    # non-interface source inheriting from an interface target
                    # is IMPLEMENTS.
                    if node.type == "Interface":
                        rel_type = "EXTENDS"
                    elif target.name in iface_names:
                        rel_type = "IMPLEMENTS"
                    else:
                        rel_type = "EXTENDS"

                    new_relationships.append(
                        Relationship(
                            source_id=node.id,
                            target_id=target.id,
                            type=rel_type,
                        )
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to resolve base class '%s' for '%s': %s",
                        base_name,
                        node.name,
                        e,
                        exc_info=True,
                    )

        # Stage 4: Package containment → Package→CONTAINS→Class/Interface
        #
        # Build a canonical package node index: module_path → first Package node seen.
        # _canonicalize_package_nodes() (called in JavaParser.parse_files) already
        # ensures exactly one Package node per module_path exists in ast_result.nodes,
        # so we just index those canonical nodes here — no re-emission needed.
        package_node_index: dict[str, ASTNode] = {}
        for node in ast_result.nodes:
            if node.type == "Package" and node.module_path:
                if node.module_path not in package_node_index:
                    package_node_index[node.module_path] = node

        # Emit one CONTAINS edge per (canonical Package, Class|Interface) pair.
        seen_contains: set[tuple[str, str]] = set()
        for node in ast_result.nodes:
            if node.type not in ("Class", "Interface"):
                continue
            pkg_name = package_index.get(node.source_file)
            if not pkg_name:
                continue
            pkg_node = package_node_index.get(pkg_name)
            if not pkg_node:
                continue
            edge_key = (pkg_node.id, node.id)
            if edge_key in seen_contains:
                continue
            seen_contains.add(edge_key)
            new_relationships.append(
                Relationship(
                    source_id=pkg_node.id,
                    target_id=node.id,
                    type="CONTAINS",
                )
            )

        return new_relationships, new_nodes
