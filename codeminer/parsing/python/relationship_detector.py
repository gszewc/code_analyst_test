"""
Relationship detector for AST Parser.

This module detects relationships between AST nodes including:
- CONTAINS (AST hierarchy)
- EXTENDS (inheritance)
- IMPLEMENTS (ABC/Protocol)
- CALLS (method calls)
- DEPENDS_ON (imports)
"""

import ast
from typing import List, Dict, Set, Optional, Tuple

from codeminer.parsing.models import ASTNode, Relationship, RelationshipType
from .nodes_visitor import ASTNodeExtractor


class RelationshipDetector:
    """Detect relationships between AST nodes."""

    @staticmethod
    def detect_all(nodes: List[ASTNode], tree: ast.AST, file_path: Optional[str] = None) -> List[Relationship]:
        """
        Detect all relationships in the AST.

        Args:
            nodes: List of ASTNodes
            tree: Parsed AST tree
            file_path: Optional file path for single-pass extraction

        Returns:
            List of detected relationships
        """
        # If file_path is provided, use single-pass extraction
        if file_path:
            extractor = ASTNodeExtractor(file_path)
            _, relationships = extractor.extract_all(tree)
            return relationships
        
        # Fallback to multi-pass detection for backward compatibility
        relationships = []

        # Detect CONTAINS relationships
        relationships.extend(
            RelationshipDetector.detect_contains_relationships(tree, nodes)
        )

        # Detect EXTENDS and IMPLEMENTS relationships
        relationships.extend(
            RelationshipDetector.detect_inheritance_relationships(tree, nodes)
        )

        # Detect CALLS relationships
        relationships.extend(
            RelationshipDetector.detect_method_calls(tree, nodes)
        )

        # Detect DEPENDS_ON relationships
        relationships.extend(
            RelationshipDetector.detect_dependencies(tree, nodes)
        )

        return relationships
    
    @staticmethod
    def detect_contains_relationships(tree: ast.AST, nodes: List[ASTNode]) -> List[Relationship]:
        """
        Detect CONTAINS relationships based on AST hierarchy.
        
        Args:
            tree: Parsed AST tree
            nodes: List of ASTNodes
            
        Returns:
            List of CONTAINS relationships
        """
        relationships = []
        
        # Find file node
        file_nodes = [n for n in nodes if n.type == 'File']
        if not file_nodes:
            return relationships
        
        file_node = file_nodes[0]
        
        # File CONTAINS all top-level classes and methods
        for node in nodes:
            if node.type in ['Class', 'Method'] and node.source_file == file_node.name:
                # Check if it's a top-level definition (not nested)
                if RelationshipDetector._is_top_level(node, tree):
                    relationships.append(Relationship(
                        source_id=file_node.id,
                        target_id=node.id,
                        type=RelationshipType.CONTAINS.value
                    ))
        
        # Class CONTAINS its methods and variables
        class_nodes = [n for n in nodes if n.type == 'Class']
        for class_node in class_nodes:
            for node in nodes:
                if node.source_file == class_node.source_file:
                    # Check if method/variable is defined within class line range
                    if (node.type in ['Method', 'Variable'] and
                        node.start_line >= class_node.start_line and
                        node.end_line <= class_node.end_line and
                        node.id != class_node.id):
                        relationships.append(Relationship(
                            source_id=class_node.id,
                            target_id=node.id,
                            type=RelationshipType.CONTAINS.value
                        ))
        
        return relationships
    
    @staticmethod
    def detect_inheritance_relationships(tree: ast.AST, nodes: List[ASTNode]) -> List[Relationship]:
        """
        Detect EXTENDS and IMPLEMENTS relationships.
        
        Args:
            tree: Parsed AST tree
            nodes: List of ASTNodes
            
        Returns:
            List of EXTENDS and IMPLEMENTS relationships
        """
        relationships = []
        
        # Build name-to-node mapping for classes
        class_nodes = [n for n in nodes if n.type == 'Class']
        class_name_to_node = {n.name: n for n in class_nodes}
        
        # Walk AST to find class definitions with bases
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.bases:
                    source_node = class_name_to_node.get(node.name)
                    if not source_node:
                        continue
                    
                    for base in node.bases:
                        base_name = None
                        if isinstance(base, ast.Name):
                            base_name = base.id
                        elif isinstance(base, ast.Attribute):
                            base_name = RelationshipDetector._get_attribute_name(base)
                        
                        if base_name:
                            # Check if it's a known class
                            if base_name in class_name_to_node:
                                target_node = class_name_to_node[base_name]
                                relationships.append(Relationship(
                                    source_id=source_node.id,
                                    target_id=target_node.id,
                                    type=RelationshipType.EXTENDS.value
                                ))
                            # Check for ABC/Protocol implementation
                            elif base_name in ['ABC', 'Protocol']:
                                relationships.append(Relationship(
                                    source_id=source_node.id,
                                    target_id=source_node.id,  # Self-reference for external ABC
                                    type=RelationshipType.IMPLEMENTS.value
                                ))
        
        return relationships
    
    @staticmethod
    def detect_method_calls(tree: ast.AST, nodes: List[ASTNode]) -> List[Relationship]:
        """
        Detect CALLS relationships between methods.
        
        Args:
            tree: Parsed AST tree
            nodes: List of ASTNodes
            
        Returns:
            List of CALLS relationships
        """
        relationships = []
        
        # Build name-to-node mapping for methods
        method_nodes = [n for n in nodes if n.type == 'Method']
        method_name_to_node = {n.name: n for n in method_nodes}
        
        # Walk AST to find Call nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Find the calling method (parent function)
                calling_method = RelationshipDetector._find_calling_method(node, tree)
                if not calling_method:
                    continue
                
                # Get called method name
                called_name = None
                if isinstance(node.func, ast.Name):
                    called_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    called_name = node.func.attr
                
                if called_name and called_name in method_name_to_node:
                    target_node = method_name_to_node[called_name]
                    relationships.append(Relationship(
                        source_id=calling_method.id,
                        target_id=target_node.id,
                        type=RelationshipType.CALLS.value
                    ))
        
        return relationships
    
    @staticmethod
    def detect_dependencies(tree: ast.AST, nodes: List[ASTNode]) -> List[Relationship]:
        """
        Detect DEPENDS_ON relationships from imports.
        
        Args:
            tree: Parsed AST tree
            nodes: List of ASTNodes
            
        Returns:
            List of DEPENDS_ON relationships
        """
        relationships = []
        
        # Track imported modules
        imports: Dict[str, str] = {}  # name -> module
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports[name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = f"{node.module}.{alias.name}"
        
        # For MVP, we track imports but don't create cross-file dependencies
        # This would require multi-file analysis which is post-MVP
        
        return relationships
    
    @staticmethod
    def _is_top_level(node: ASTNode, tree: ast.AST) -> bool:
        """Check if a node is defined at top level (not nested in class/function)."""
        for parent in ast.walk(tree):
            if isinstance(parent, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if node is within this parent's body
                for child in ast.walk(parent):
                    if hasattr(child, 'lineno') and child.lineno == node.start_line:
                        if parent.lineno < child.lineno < (parent.end_lineno or parent.lineno + 100):
                            # Check if parent is direct (not grandparent)
                            return parent.lineno < node.start_line and node.end_line <= (parent.end_lineno or parent.lineno + 100)
        return True
    
    @staticmethod
    def _find_calling_method(call_node: ast.Call, tree: ast.AST) -> ASTNode:
        """Find the method that contains this call node."""
        # This is a simplified implementation
        # A full implementation would need parent tracking
        return None
    
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
