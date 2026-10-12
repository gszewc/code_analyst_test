"""
AST Node Visitor for Python AST parsing.

This module provides a NodeVisitor-based approach to extract nodes and
detect relationships in a single AST traversal.
"""

import ast
import uuid
from pathlib import Path
from logging import getLogger
from typing import Dict, List, Optional, Set, Tuple, Any

from codeminer.parsing.models import ASTNode, Relationship, RelationshipType, NodeType, RawImport, UnresolvedReference
from .path_normalization import PathNormalizationError, normalize_source_file_path


logger = getLogger(__name__)



class ASTNodeExtractor(ast.NodeVisitor):
    """
    Extracts nodes and relationships from Python AST in a single pass.

    Uses ast.NodeVisitor pattern for efficient traversal with context tracking.
    """

    def __init__(
        self,
        file_path: str,
        includeImports: bool = False,
        project_root: Optional[str] = None,
    ):
        """
        Initialize the extractor.

        Args:
            file_path: Path to the Python source file
            includeImports: Whether to include import nodes
        """
        self.file_path = file_path
        self.includeImports = includeImports
        self.project_root = project_root
        self.nodes: List[ASTNode] = []
        self.relationships: List[Relationship] = []
        self.normalization_errors: List[str] = []
        
        # Context tracking
        self.current_class: Optional[ASTNode] = None
        self.current_function: Optional[ASTNode] = None
        self.class_stack: List[ASTNode] = []
        self.function_stack: List[ASTNode] = []
        
        # Relationship metadata collected during traversal
        self._class_name_to_node: Dict[str, ASTNode] = {}
        self._method_name_to_node: Dict[str, ASTNode] = {}
        self._imports: Dict[str, str] = {}  # alias -> module
        self._pending_calls: List[Tuple[ast.Call, Optional[ASTNode]]] = []
        self._pending_inherits: List[Tuple[str, List[str], ASTNode]] = []
        self._raw_imports: List[RawImport] = []
        self._unresolved_references: List[UnresolvedReference] = []

        # File node
        self._file_node: Optional[ASTNode] = None

    def _source_file(self) -> str:
        """Return normalized source_file or fallback to POSIX path on failure."""
        if not self.project_root:
            return Path(self.file_path).as_posix()

        try:
            return normalize_source_file_path(self.file_path, self.project_root)
        except PathNormalizationError as exc:
            message = str(exc)
            self.normalization_errors.append(message)
            logger.warning(
                "Path normalization failed for '%s' against root '%s': %s. Falling back to raw path.",
                self.file_path,
                self.project_root,
                message,
            )
            return Path(self.file_path).as_posix()

    def visit(self, node: ast.AST) -> Any:
        """Visit a node and return the result."""
        return super().visit(node)

    def generic_visit(self, node: ast.AST) -> Any:
        """Visit all child nodes."""
        for child in ast.iter_child_nodes(node):
            self.visit(child)

    def extract_all(self, tree: ast.AST) -> Tuple[List[ASTNode], List[Relationship], List[RawImport], List[UnresolvedReference]]:
        """
        Extract all nodes and relationships from the AST.

        Args:
            tree: Parsed AST tree

        Returns:
            Tuple of (nodes, relationships, raw_imports, unresolved_references)
        """
        # Create file node first
        self._create_file_node(tree)

        # Visit all nodes
        self.visit(tree)

        # Process pending relationships
        self._process_pending_inherits()
        self._process_pending_calls()

        return self.nodes, self.relationships, self._raw_imports, self._unresolved_references

    def _create_file_node(self, tree: ast.AST) -> None:
        """Create the file/module node."""
        
        body = tree.body if hasattr(tree, 'body') else []
        end_line = body[len(body)-1].end_lineno if isinstance(body, list) and body else 0
        self._file_node = ASTNode(
            id=self._generate_node_id(),
            type=NodeType.FILE.value,
            name=Path(self.file_path).name,
            source_file=self._source_file(),
            start_line=1,
            end_line=end_line,
            start_column=0,
            end_column=0,
            signature=None,
            decorators=None,
            base_classes=None,
            data_type=None
        )
        self.nodes.append(self._file_node)

    def _generate_node_id(self) -> str:
        """Generate a unique UUID for a node."""
        return str(uuid.uuid4())

    def _get_attribute_name(self, attr: ast.Attribute) -> str:
        """Get full attribute name (e.g., 'module.Class')."""
        parts = []
        current = attr
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))

    def _extract_decorators(self, node) -> List[str]:
        """Extract decorator names from a node."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(self._get_attribute_name(decorator))
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator.func, ast.Attribute):
                    decorators.append(self._get_attribute_name(decorator.func))
        return decorators

    def _extract_parameters(self, node) -> str:
        """Extract parameter string from function definition."""
        params = []

        # Regular arguments
        for arg in node.args.args:
            param = arg.arg
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param += f": {arg.annotation.id}"
                elif isinstance(arg.annotation, ast.Attribute):
                    param += f": {self._get_attribute_name(arg.annotation)}"
            params.append(param)

        # *args
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")

        # **kwargs
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        return ", ".join(params)

    def _get_name(self, node: ast.expr) -> str:
        """Extract name from an AST expression."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return self._get_name(node.value)
        return "Unknown"

    # ========== Visit Methods ==========

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_attribute_name(base))

        # Extract decorators
        decorators = self._extract_decorators(node)

        # Build signature
        signature = f"class {node.name}"
        if base_classes:
            signature += f"({', '.join(base_classes)})"

        # Get end line
        end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno

        # Create class node
        class_node = ASTNode(
            id=self._generate_node_id(),
            type=NodeType.CLASS.value,
            name=node.name,
            source_file=self._source_file(),
            start_line=node.lineno,
            end_line=end_line,
            start_column=node.col_offset,
            end_column=0,
            signature=signature,
            decorators=decorators,
            base_classes=base_classes,
            data_type=None
        )
        self.nodes.append(class_node)
        self._class_name_to_node[node.name] = class_node

        # Track inheritance for relationship detection
        if base_classes:
            self._pending_inherits.append((node.name, base_classes, class_node))

        # Create CONTAINS relationship from file to top-level class
        if self._file_node and not self.current_class:
            self.relationships.append(Relationship(
                source_id=self._file_node.id,
                target_id=class_node.id,
                type=RelationshipType.CONTAINS.value
            ))

        # Push class context
        parent_class = self.current_class
        self.current_class = class_node
        self.class_stack.append(class_node)

        # Visit child nodes
        self.generic_visit(node)

        # Pop class context
        self.class_stack.pop()
        self.current_class = parent_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self._handle_function(node, is_async=True)

    def _handle_function(self, node, is_async: bool) -> None:
        """Handle function/method definition."""
        # Extract decorators
        decorators = self._extract_decorators(node)

        # Extract parameters
        params = self._extract_parameters(node)

        # Extract return type
        return_type = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                return_type = self._get_attribute_name(node.returns)
            elif isinstance(node.returns, ast.Constant):
                return_type = str(node.returns.value)

        # Build signature
        signature = f"def {node.name}({params})"
        if return_type:
            signature += f" -> {return_type}"

        # Get end line
        end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno

        # Determine if it's a method or function
        is_method = self.current_class is not None
        node_type = NodeType.METHOD.value if is_method else NodeType.FUNCTION.value

        # Create method/function node
        func_node = ASTNode(
            id=self._generate_node_id(),
            type=node_type,
            name=node.name,
            source_file=self._source_file(),
            start_line=node.lineno,
            end_line=end_line,
            start_column=node.col_offset,
            end_column=0,
            signature=signature,
            decorators=decorators,
            base_classes=None,
            data_type=return_type
        )
        self.nodes.append(func_node)
        self._method_name_to_node[node.name] = func_node

        # Create CONTAINS relationship
        if self.current_class:
            # Method belongs to class
            self.relationships.append(Relationship(
                source_id=self.current_class.id,
                target_id=func_node.id,
                type=RelationshipType.CONTAINS.value
            ))
        elif self._file_node:
            # Top-level function belongs to file
            self.relationships.append(Relationship(
                source_id=self._file_node.id,
                target_id=func_node.id,
                type=RelationshipType.CONTAINS.value
            ))

        # Push function context
        parent_function = self.current_function
        self.current_function = func_node
        self.function_stack.append(func_node)

        # Visit child nodes (including Call nodes for CALLS relationships)
        self.generic_visit(node)

        # Pop function context
        self.function_stack.pop()
        self.current_function = parent_function

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments (class/module variables)."""
        if not isinstance(node.target, ast.Name):
            return

        # Only process class-level or module-level variables
        if not self.current_class and not self._file_node:
            return

        # Get variable name
        name = node.target.id

        # Get type annotation
        data_type = None
        if node.annotation:
            if isinstance(node.annotation, ast.Name):
                data_type = node.annotation.id
            elif isinstance(node.annotation, ast.Attribute):
                data_type = self._get_attribute_name(node.annotation)
            elif isinstance(node.annotation, ast.Subscript):
                if isinstance(node.annotation.value, ast.Name):
                    data_type = node.annotation.value.id

        # Get end line
        end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno

        # Create variable node
        var_node = ASTNode(
            id=self._generate_node_id(),
            type=NodeType.VARIABLE.value,
            name=name,
            source_file=self._source_file(),
            start_line=node.lineno,
            end_line=end_line,
            start_column=node.col_offset,
            end_column=0,
            signature=None,
            decorators=None,
            base_classes=None,
            data_type=data_type
        )
        self.nodes.append(var_node)

        # Create CONTAINS relationship
        if self.current_class:
            self.relationships.append(Relationship(
                source_id=self.current_class.id,
                target_id=var_node.id,
                type=RelationshipType.CONTAINS.value
            ))
        elif self._file_node:
            self.relationships.append(Relationship(
                source_id=self._file_node.id,
                target_id=var_node.id,
                type=RelationshipType.CONTAINS.value
            ))

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        # Always collect raw imports for cross-file resolution
        for alias in node.names:
            name = alias.asname or alias.name
            self._imports[name] = alias.name
            self._raw_imports.append(RawImport(
                source_file=self._source_file(),
                source_file_node_id=self._file_node.id,
                module=alias.name,
                names=[alias.name],
                level=0,
            ))

        if not self.includeImports:
            self.generic_visit(node)
            return

        for alias in node.names:
            name = alias.asname or alias.name
            import_node = ASTNode(
                id=self._generate_node_id(),
                type=NodeType.IMPORT.value,
                name=name,
                source_file=self._source_file(),
                start_line=node.lineno,
                end_line=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                start_column=node.col_offset,
                end_column=0,
            )
            self.nodes.append(import_node)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statements."""
        # Always collect raw imports and populate _imports dict
        names = [alias.name for alias in node.names] if node.names else []
        for alias in (node.names or []):
            name = alias.asname or alias.name
            if node.module:
                self._imports[name] = f"{node.module}.{alias.name}"
            else:
                self._imports[name] = alias.name

        self._raw_imports.append(RawImport(
            source_file=self._source_file(),
            source_file_node_id=self._file_node.id,
            module=node.module,
            names=names,
            level=node.level or 0,
        ))

        if not self.includeImports:
            self.generic_visit(node)
            return

        for alias in (node.names or []):
            name = alias.asname or alias.name
            import_node = ASTNode(
                id=self._generate_node_id(),
                type=NodeType.IMPORT.value,
                name=name,
                source_file=self._source_file(),
                start_line=node.lineno,
                end_line=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                start_column=node.col_offset,
                end_column=0,
            )
            self.nodes.append(import_node)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function/method calls."""
        # Track call for later processing (when we know the calling context)
        if self.current_function:
            self._pending_calls.append((node, self.current_function))
        
        self.generic_visit(node)

    # ========== Post-processing Methods ==========

    def _process_pending_inherits(self) -> None:
        """Process inheritance relationships."""
        for class_name, base_classes, source_node in self._pending_inherits:
            for base_name in base_classes:
                # Check if it's a known class
                if base_name in self._class_name_to_node:
                    target_node = self._class_name_to_node[base_name]
                    self.relationships.append(Relationship(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        type=RelationshipType.EXTENDS.value
                    ))
                # # Check for ABC/Protocol implementation
                # elif base_name in ['ABC', 'Protocol']:
                #     self.relationships.append(Relationship(
                #         source_id=source_node.id,
                #         target_id=source_node.id,  # Self-reference for external ABC
                #         type=RelationshipType.IMPLEMENTS.value
                #     ))

    def _process_pending_calls(self) -> None:
        """Process method call relationships and emit unresolved references."""
        for call_node, calling_func in self._pending_calls:
            called_name = None
            if isinstance(call_node.func, ast.Name):
                called_name = call_node.func.id
            elif isinstance(call_node.func, ast.Attribute):
                called_name = call_node.func.attr

            if called_name and called_name in self._method_name_to_node:
                target_node = self._method_name_to_node[called_name]
                if calling_func.id != target_node.id:
                    self.relationships.append(Relationship(
                        source_id=calling_func.id,
                        target_id=target_node.id,
                        type=RelationshipType.CALLS.value
                    ))
            elif called_name:
                # Emit as unresolved reference for cross-file resolution
                # Build full reference name for attribute calls
                if isinstance(call_node.func, ast.Attribute):
                    ref_name = self._get_attribute_name(call_node.func)
                else:
                    ref_name = called_name
                self._unresolved_references.append(UnresolvedReference(
                    source_file=self._source_file(),
                    source_node_id=calling_func.id,
                    reference_name=ref_name,
                    reference_type="call",
                    line=call_node.lineno,
                ))

    def get_imports(self) -> Dict[str, str]:
        """Get collected imports."""
        return self._imports


class NodeBuilder:
    """
    Backward-compatible wrapper around ASTNodeExtractor.
    
    This class maintains the original API while using the new NodeVisitor-based
    implementation internally.
    """

    @staticmethod
    def generate_node_id() -> str:
        """
        Generate a unique UUID for a node.

        Returns:
            UUID string
        """
        return str(uuid.uuid4())

    @staticmethod
    def build_nodes(tree: ast.AST, file_path: str) -> List[ASTNode]:
        """
        Build list of ASTNodes from AST tree.

        Args:
            tree: Parsed AST tree
            file_path: Path to source file

        Returns:
            List of ASTNode objects
        """
        extractor = ASTNodeExtractor(file_path)
        nodes, _, _, _ = extractor.extract_all(tree)
        return nodes

    @staticmethod
    def build_file_node(file_path: str, tree: ast.AST) -> ASTNode:
        """
        Build ASTNode for a file/module.

        Args:
            file_path: Path to source file
            tree: Parsed AST tree

        Returns:
            ASTNode representing the file
        """
        extractor = ASTNodeExtractor(file_path)
        extractor._create_file_node(tree)
        return extractor._file_node

    @staticmethod
    def build_class_node(node: ast.ClassDef, file_path: str) -> ASTNode:
        """
        Build ASTNode from ClassDef.

        Args:
            node: ClassDef AST node
            file_path: Path to source file

        Returns:
            ASTNode representing the class
        """
        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(NodeBuilder._get_attribute_name(base))

        # Extract decorators
        decorators = NodeBuilder._extract_decorators(node)

        # Build signature
        signature = f"class {node.name}"
        if base_classes:
            signature += f"({', '.join(base_classes)})"

        # Get end line
        end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno

        return ASTNode(
            id=NodeBuilder.generate_node_id(),
            type=NodeType.CLASS.value,
            name=node.name,
            source_file=file_path,
            start_line=node.lineno,
            end_line=end_line,
            start_column=node.col_offset,
            end_column=0,
            signature=signature,
            decorators=decorators,
            base_classes=base_classes,
            data_type=None
        )

    @staticmethod
    def build_method_node(node: ast.FunctionDef, file_path: str) -> ASTNode:
        """
        Build ASTNode from FunctionDef.

        Args:
            node: FunctionDef AST node
            file_path: Path to source file

        Returns:
            ASTNode representing the method
        """
        # Extract decorators
        decorators = NodeBuilder._extract_decorators(node)

        # Extract parameters
        params = NodeBuilder._extract_parameters(node)

        # Extract return type
        return_type = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                return_type = NodeBuilder._get_attribute_name(node.returns)
            elif isinstance(node.returns, ast.Constant):
                return_type = str(node.returns.value)

        # Build signature
        signature = f"def {node.name}({params})"
        if return_type:
            signature += f" -> {return_type}"

        # Get end line
        end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno

        return ASTNode(
            id=NodeBuilder.generate_node_id(),
            type=NodeType.METHOD.value,
            name=node.name,
            source_file=file_path,
            start_line=node.lineno,
            end_line=end_line,
            start_column=node.col_offset,
            end_column=0,
            signature=signature,
            decorators=decorators,
            base_classes=None,
            data_type=return_type
        )

    @staticmethod
    def build_variable_node(node: ast.AnnAssign, file_path: str) -> ASTNode:
        """
        Build ASTNode from annotated assignment (class variable).

        Args:
            node: AnnAssign AST node
            file_path: Path to source file

        Returns:
            ASTNode representing the variable
        """
        # Get variable name
        if isinstance(node.target, ast.Name):
            name = node.target.id
        else:
            return None

        # Get type annotation
        data_type = None
        if node.annotation:
            if isinstance(node.annotation, ast.Name):
                data_type = node.annotation.id
            elif isinstance(node.annotation, ast.Attribute):
                data_type = NodeBuilder._get_attribute_name(node.annotation)
            elif isinstance(node.annotation, ast.Subscript):
                # Handle generic types like List[int]
                if isinstance(node.annotation.value, ast.Name):
                    data_type = node.annotation.value.id

        # Get end line
        end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno

        return ASTNode(
            id=NodeBuilder.generate_node_id(),
            type=NodeType.VARIABLE.value,
            name=name,
            source_file=file_path,
            start_line=node.lineno,
            end_line=end_line,
            start_column=node.col_offset,
            end_column=0,
            signature=None,
            decorators=None,
            base_classes=None,
            data_type=data_type
        )

    @staticmethod
    def _extract_decorators(node) -> List[str]:
        """Extract decorator names from a node."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(NodeBuilder._get_attribute_name(decorator))
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator.func, ast.Attribute):
                    decorators.append(NodeBuilder._get_attribute_name(decorator.func))
        return decorators

    @staticmethod
    def _extract_parameters(node) -> str:
        """Extract parameter string from function definition."""
        params = []

        # Regular arguments
        for arg in node.args.args:
            param = arg.arg
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param += f": {arg.annotation.id}"
                elif isinstance(arg.annotation, ast.Attribute):
                    param += f": {NodeBuilder._get_attribute_name(arg.annotation)}"
            params.append(param)

        # *args
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")

        # **kwargs
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        return ", ".join(params)

    @staticmethod
    def _get_attribute_name(attr: ast.Attribute) -> str:
        """Get full attribute name (e.g., 'module.Class')."""
        parts = []
        current = attr
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))

    @staticmethod
    def _is_class_level(node: ast.AnnAssign, tree: ast.AST) -> bool:
        """Check if an assignment is at class level."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in parent.body:
                    if child is node:
                        return True
        return False
