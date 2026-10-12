"""JavaParser — tree-sitter-based Java language parser."""

import uuid
from logging import getLogger
from typing import Any

import tree_sitter_java

from codeminer.parsing.treesitter.base import TreeSitterLanguageParser
from codeminer.parsing.interfaces import CrossFileResolverBase
from codeminer.parsing.models import ASTNode, ASTResult, RawImport, Relationship
from codeminer.parsing.types import NodeTypeDefinition, RelationshipTypeDefinition

logger = getLogger(__name__)


class JavaParser(TreeSitterLanguageParser):
    """Java language parser using tree-sitter."""

    def _load_language(self) -> Any:
        return tree_sitter_java.language()

    def get_language_name(self) -> str:
        return "java"

    def get_supported_extensions(self) -> list[str]:
        return [".java"]

    def get_excluded_dirs(self) -> set[str]:
        return {"target", "build", ".gradle", ".idea"}

    def get_node_type_definitions(self) -> list[NodeTypeDefinition]:
        lang = "java"
        return [
            NodeTypeDefinition(
                name="File",
                language=lang,
                category="structure",
                description="Java source file",
            ),
            NodeTypeDefinition(
                name="Package",
                language=lang,
                category="structure",
                description="Package declaration",
            ),
            NodeTypeDefinition(
                name="Class",
                language=lang,
                category="structure",
                description="Class definition",
            ),
            NodeTypeDefinition(
                name="Interface",
                language=lang,
                category="structure",
                description="Interface definition",
            ),
            NodeTypeDefinition(
                name="Enum",
                language=lang,
                category="structure",
                description="Enum definition",
            ),
            NodeTypeDefinition(
                name="Method",
                language=lang,
                category="callable",
                description="Method definition",
            ),
            NodeTypeDefinition(
                name="Constructor",
                language=lang,
                category="callable",
                description="Constructor definition",
            ),
            NodeTypeDefinition(
                name="Variable",
                language=lang,
                category="data",
                description="Field/variable declaration",
            ),
            NodeTypeDefinition(
                name="Import",
                language=lang,
                category="dependency",
                description="Import statement",
            ),
            NodeTypeDefinition(
                name="ExternalModule",
                language=lang,
                category="dependency",
                description="External module reference",
            ),
        ]

    def get_relationship_type_definitions(self) -> list[RelationshipTypeDefinition]:
        lang = "java"
        return [
            RelationshipTypeDefinition(
                name="CONTAINS",
                language=lang,
                category="structural",
                description="Parent contains child",
            ),
            RelationshipTypeDefinition(
                name="EXTENDS",
                language=lang,
                category="inheritance",
                description="Class/interface inheritance",
            ),
            RelationshipTypeDefinition(
                name="IMPLEMENTS",
                language=lang,
                category="inheritance",
                description="Interface implementation",
            ),
            RelationshipTypeDefinition(
                name="DEPENDS_ON",
                language=lang,
                category="dependency",
                description="File-level dependency",
            ),
            RelationshipTypeDefinition(
                name="IMPORTS",
                language=lang,
                category="dependency",
                description="Import relationship",
            ),
        ]

    def _get_node_queries(self) -> dict[str, str]:
        return {
            "Package": "(package_declaration (scoped_identifier) @name) @node",
            "Import": "(import_declaration (scoped_identifier) @name) @node",
            "Class": "(class_declaration name: (identifier) @name) @node",
            "Interface": "(interface_declaration name: (identifier) @name) @node",
            "Enum": "(enum_declaration name: (identifier) @name) @node",
            "Method": "(method_declaration name: (identifier) @name) @node",
            "Constructor": "(constructor_declaration name: (identifier) @name) @node",
            "Variable": "(field_declaration declarator: (variable_declarator name: (identifier) @name)) @node",
        }

    def _map_node(
        self,
        ts_node,
        node_type: str,
        name: str,
        source_file: str,
        project_root: str | None,
    ) -> ASTNode:
        node_id = str(uuid.uuid4())

        # Extract signature for methods/constructors
        signature = None
        if node_type in ("Method", "Constructor"):
            params_node = ts_node.child_by_field_name("parameters")
            if params_node:
                params_text = params_node.text
                if isinstance(params_text, bytes):
                    params_text = params_text.decode("utf-8")
                # Include return type for methods
                type_node = ts_node.child_by_field_name("type")
                if type_node and node_type == "Method":
                    type_text = type_node.text
                    if isinstance(type_text, bytes):
                        type_text = type_text.decode("utf-8")
                    signature = f"{type_text} {name}{params_text}"
                else:
                    signature = f"{name}{params_text}"

        # Extract base classes and annotations for Class/Interface nodes
        base_classes = None
        decorators = None
        if node_type == "Class":
            base_classes = self._extract_class_bases(ts_node)
            decorators = self._extract_annotations(ts_node)
            signature = f"class {name}"
            if base_classes:
                signature += f"({', '.join(base_classes)})"
        elif node_type == "Interface":
            base_classes = self._extract_interface_bases(ts_node)
            decorators = self._extract_annotations(ts_node)
            signature = f"class {name}"
            if base_classes:
                signature += f"({', '.join(base_classes)})"

        # Extract module_path for imports and packages
        module_path = None
        if node_type in ("Import", "Package"):
            module_path = name  # name is already the full scoped_identifier text

        # For Import nodes, also record raw import data
        if node_type == "Import":
            parts = name.rsplit(".", 1)
            simple_name = parts[-1] if len(parts) > 1 else name
            self._pending_raw_imports.append(
                RawImport(
                    source_file=source_file,
                    source_file_node_id=self._current_file_node_id,
                    module=name,
                    names=[simple_name],
                    level=0,
                )
            )

        return ASTNode(
            id=node_id,
            type=node_type,
            name=name,
            source_file=source_file,
            start_line=ts_node.start_point[0] + 1,
            end_line=ts_node.end_point[0] + 1,
            start_column=ts_node.start_point[1],
            end_column=ts_node.end_point[1],
            signature=signature,
            base_classes=base_classes,
            module_path=module_path,
            decorators=decorators or None,
        )

    def _extract_class_bases(self, ts_node) -> list[str] | None:
        """Extract extends/implements names from a class declaration.

        Tree-sitter-java grammar:
          - superclass field: superclass node with direct type_identifier children
          - interfaces field: super_interfaces node → type_list → type_identifier children
        """
        bases = []

        # Check for superclass: extends Animal
        superclass = ts_node.child_by_field_name("superclass")
        if superclass:
            for child in superclass.children:
                if child.type == "type_identifier":
                    text = (
                        child.text.decode("utf-8")
                        if isinstance(child.text, bytes)
                        else str(child.text)
                    )
                    bases.append(text)

        # Check for interfaces: implements Foo, Bar
        # Field name is "interfaces", node type is "super_interfaces"
        interfaces = ts_node.child_by_field_name("interfaces")
        if interfaces:
            for child in interfaces.children:
                if child.type == "type_list":
                    for type_child in child.children:
                        if type_child.type == "type_identifier":
                            text = (
                                type_child.text.decode("utf-8")
                                if isinstance(type_child.text, bytes)
                                else str(type_child.text)
                            )
                            bases.append(text)

        return bases if bases else None

    def _extract_interface_bases(self, ts_node) -> list[str] | None:
        """Extract extends names from an interface declaration.

        Tree-sitter-java grammar:
          - extends_interfaces is a named child (not a field) of type extends_interfaces
          - extends_interfaces node → type_list → type_identifier children
        """
        bases = []

        # extends_interfaces is a child node, not a field — iterate children
        for child in ts_node.children:
            if child.type == "extends_interfaces":
                for subchild in child.children:
                    if subchild.type == "type_list":
                        for type_child in subchild.children:
                            if type_child.type == "type_identifier":
                                text = (
                                    type_child.text.decode("utf-8")
                                    if isinstance(type_child.text, bytes)
                                    else str(type_child.text)
                                )
                                bases.append(text)

        return bases if bases else None

    def _extract_annotations(self, ts_node) -> list[str]:
        """Extract annotation names from a class or interface declaration.

        Annotations appear inside the ``modifiers`` child as ``marker_annotation``
        (``@Foo``) or ``annotation`` (``@Foo(...)``) nodes, each with a ``name``
        field containing the annotation identifier.
        """
        annotations = []
        modifiers = next(
            (c for c in ts_node.children if c.type == "modifiers"), None
        )
        if modifiers is None:
            return annotations
        for child in modifiers.children:
            if child.type in ("marker_annotation", "annotation"):
                for subchild in child.children:
                    if subchild.type == "identifier":
                        text = subchild.text
                        if isinstance(text, bytes):
                            text = text.decode("utf-8")
                        annotations.append(text)
                        break
        return annotations

    def _extract_intra_file_relationships(
        self, nodes: list[ASTNode], tree
    ) -> list[Relationship]:
        """Build CONTAINS relationships from node line ranges."""
        if len(nodes) < 2:
            return []

        relationships = []
        # Sort by start_line ascending, then by range size descending (largest first)
        sorted_nodes = sorted(
            nodes,
            key=lambda n: (n.start_line, -(n.end_line - n.start_line)),
        )

        for i, child in enumerate(sorted_nodes):
            # Find the closest enclosing parent (smallest range that fully contains child)
            best_parent = None
            best_range = float("inf")
            for j, parent in enumerate(sorted_nodes):
                if i == j:
                    continue
                if (
                    parent.start_line <= child.start_line
                    and parent.end_line >= child.end_line
                    and not (
                        parent.start_line == child.start_line
                        and parent.end_line == child.end_line
                        and parent.type == child.type
                    )
                ):
                    parent_range = parent.end_line - parent.start_line
                    if parent_range < best_range:
                        best_range = parent_range
                        best_parent = parent

            if best_parent is not None:
                relationships.append(
                    Relationship(
                        source_id=best_parent.id,
                        target_id=child.id,
                        type="CONTAINS",
                    )
                )

        return relationships

    def parse_file(self, file_path: str, project_root: str | None = None) -> ASTResult:
        """Override to set file node id before extraction."""
        # Reset per-file state
        self._pending_raw_imports = []
        self._current_file_node_id = ""

        # Generate file node id now so raw_imports can reference it
        self._current_file_node_id = str(uuid.uuid4())

        result = super().parse_file(file_path, project_root)

        # Replace the auto-generated File node id with our pre-generated one
        # so that raw_imports reference the correct file node id
        for node in result.nodes:
            if node.type == "File":
                old_id = node.id
                node.id = self._current_file_node_id
                # Update any CONTAINS relationships referencing the old id
                for rel in result.relationships:
                    if rel.source_id == old_id:
                        rel.source_id = self._current_file_node_id
                    if rel.target_id == old_id:
                        rel.target_id = self._current_file_node_id
                break

        return result

    def parse_files(
        self, file_paths: list[str], project_root: str | None = None
    ) -> ASTResult:
        """Parse multiple Java files and canonicalize package nodes by module_path."""
        result = super().parse_files(file_paths, project_root)
        self._canonicalize_package_nodes(result)
        return result

    @staticmethod
    def _canonicalize_package_nodes(result: ASTResult) -> None:
        """Keep the first Package node per module_path and rewire relationships."""
        canonical_packages: dict[str, ASTNode] = {}
        replacement_ids: dict[str, str] = {}
        deduped_nodes: list[ASTNode] = []

        for node in result.nodes:
            if node.type != "Package" or not node.module_path:
                deduped_nodes.append(node)
                continue

            canonical_node = canonical_packages.get(node.module_path)
            if canonical_node is None:
                canonical_packages[node.module_path] = node
                deduped_nodes.append(node)
                continue

            replacement_ids[node.id] = canonical_node.id

        if not replacement_ids:
            return

        for rel in result.relationships:
            rel.source_id = replacement_ids.get(rel.source_id, rel.source_id)
            rel.target_id = replacement_ids.get(rel.target_id, rel.target_id)

        result.nodes = deduped_nodes

        if result.summary is not None:
            result.summary.total_nodes = len(result.nodes)
            result.summary.nodes_by_type = {}
            for node in result.nodes:
                result.summary.nodes_by_type[node.type] = (
                    result.summary.nodes_by_type.get(node.type, 0) + 1
                )

    def create_cross_file_resolver(self) -> CrossFileResolverBase | None:
        from .cross_file_resolver import JavaCrossFileResolver

        return JavaCrossFileResolver()
