"""
Node builder for AST Parser.

This module builds ASTNode objects from Python AST trees.
"""

import ast
import uuid
from pathlib import Path
from typing import List
from codeminer.parsing.models import ASTNode, NodeType


class NodeBuilder:
    """Build ASTNode objects from Python AST."""
    
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
        nodes = []
        
        # Create file node
        file_node = NodeBuilder.build_file_node(file_path, tree)
        nodes.append(file_node)
        
        # Walk tree and create nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                nodes.append(NodeBuilder.build_class_node(node, file_path))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes.append(NodeBuilder.build_method_node(node, file_path))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                # Class-level annotated assignments (variables)
                if NodeBuilder._is_class_level(node, tree):
                    nodes.append(NodeBuilder.build_variable_node(node, file_path))
        
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
        # Get line count from tree
        end_line = tree.end_lineno if hasattr(tree, 'end_lineno') and tree.end_lineno else 1
        
        return ASTNode(
            id=NodeBuilder.generate_node_id(),
            type=NodeType.FILE.value,
            name=Path(file_path).name,
            source_file=file_path,
            start_line=1,
            end_line=end_line,
            start_column=0,
            end_column=0,
            signature=None,
            decorators=None,
            base_classes=None,
            data_type=None
        )
    
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
