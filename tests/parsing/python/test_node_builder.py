"""Tests for NodeBuilder component."""

import os
import ast
import pytest

from codeminer.parsing.python.node_builder import NodeBuilder
from codeminer.parsing.python.nodes_visitor import ASTNodeExtractor
from codeminer.parsing.models import NodeType


class TestNodeBuilder:
    """Test NodeBuilder functionality."""
    
    def test_build_file_node(self):
        """Test building a file node."""
        source = "def func(): pass"
        tree = ast.parse(source)
        file_path = "/test/file.py"

        node = NodeBuilder.build_file_node(file_path, tree)

        assert node.type == 'File'
        assert node.name == 'file.py'
        assert node.source_file == file_path
        assert node.start_line == 1
    
    def test_build_class_node(self):
        """Test building a class node."""
        source = """
class MyClass(BaseClass):
    pass
"""
        tree = ast.parse(source)
        class_def = tree.body[0]
        file_path = "/test/file.py"
        
        node = NodeBuilder.build_class_node(class_def, file_path)
        
        assert node.type == 'Class'
        assert node.name == 'MyClass'
        assert 'BaseClass' in node.base_classes
    
    def test_build_method_node(self):
        """Test building a method node."""
        source = """
def my_method(self, x: int, y: str = "default") -> bool:
    pass
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        file_path = "/test/file.py"
        
        node = NodeBuilder.build_method_node(func_def, file_path)
        
        assert node.type == 'Method'
        assert node.name == 'my_method'
        assert 'x: int' in node.signature
        assert '-> bool' in node.signature
    
    def test_build_nodes_from_tree(self):
        """Test building all nodes from an AST tree."""
        source = """
class MyClass:
    def method_one(self):
        pass
    
    def method_two(self):
        pass

def standalone():
    pass
"""
        tree = ast.parse(source)
        file_path = "/test/file.py"
        
        nodes = NodeBuilder.build_nodes(tree, file_path)
        
        assert len(nodes) > 0
        
        # Check for expected node types
        types = [n.type for n in nodes]
        assert 'File' in types
        assert 'Class' in types
        assert 'Method' in types
    
    def test_generate_node_id(self):
        """Test that node IDs are unique UUIDs."""
        id1 = NodeBuilder.generate_node_id()
        id2 = NodeBuilder.generate_node_id()
        
        assert id1 != id2
        assert len(id1) == 36  # UUID format
    
    def test_extract_decorators(self):
        """Test decorator extraction."""
        source = """
@decorator_one
@decorator_two
class MyClass:
    pass
"""
        tree = ast.parse(source)
        class_def = tree.body[0]
        
        decorators = NodeBuilder._extract_decorators(class_def)
        
        assert 'decorator_one' in decorators
        assert 'decorator_two' in decorators
    
    def test_extract_parameters(self):
        """Test parameter extraction."""
        source = """
def func(a, b: int, *args, **kwargs):
    pass
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        
        params = NodeBuilder._extract_parameters(func_def)
        
        assert 'a' in params
        assert 'b: int' in params

    def test_extractor_normalizes_source_file_for_all_emitted_node_types(self, tmp_path):
        """ASTNodeExtractor should emit normalized source_file when project_root is set."""
        source = """
import os
from pathlib import Path

class MyClass:
    value: int = 1

    def method(self):
        return os.getcwd()

def standalone():
    return Path('.')
"""
        tree = ast.parse(source)
        project_root = tmp_path / "uploads" / "project-1235" / "source"
        target_file = project_root / "application" / "app.py"
        target_file.parent.mkdir(parents=True)
        target_file.write_text(source, encoding="utf-8")

        extractor = ASTNodeExtractor(
            str(target_file),
            includeImports=True,
            project_root=str(project_root),
        )
        nodes, *_ = extractor.extract_all(tree)

        assert len(nodes) > 0
        assert all(node.source_file == "application/app.py" for node in nodes)
        assert any(node.type == 'File' for node in nodes)
        assert any(node.type == 'Class' for node in nodes)
        assert any(node.type == 'Method' for node in nodes)
        assert any(node.type == 'Function' for node in nodes)
        assert any(node.type == 'Variable' for node in nodes)
        assert any(node.type == 'Import' for node in nodes)
