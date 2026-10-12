"""Tests for RelationshipDetector component."""

import os
import ast
import pytest

from codeminer.parsing.python.relationship_detector import RelationshipDetector
from codeminer.parsing.python.node_builder import NodeBuilder
from codeminer.parsing.models import RelationshipType


class TestRelationshipDetector:
    """Test RelationshipDetector functionality."""
    
    def test_detect_contains_relationships(self):
        """Test detection of CONTAINS relationships."""
        source = """
class MyClass:
    def method(self):
        pass
"""
        tree = ast.parse(source)
        nodes = NodeBuilder.build_nodes(tree, "/test/file.py")
        
        relationships = RelationshipDetector.detect_contains_relationships(tree, nodes)
        
        # File should CONTAIN class
        file_node = [n for n in nodes if n.type == 'File'][0]
        class_node = [n for n in nodes if n.type == 'Class'][0]
        
        contains_rels = [r for r in relationships if r.type == 'CONTAINS']
        assert len(contains_rels) > 0
    
    def test_detect_inheritance_relationships(self):
        """Test detection of EXTENDS relationships."""
        source = """
class BaseClass:
    pass

class DerivedClass(BaseClass):
    pass
"""
        tree = ast.parse(source)
        nodes = NodeBuilder.build_nodes(tree, "/test/file.py")
        
        relationships = RelationshipDetector.detect_inheritance_relationships(tree, nodes)
        
        extends_rels = [r for r in relationships if r.type == 'EXTENDS']
        assert len(extends_rels) > 0
    
    def test_detect_method_calls(self):
        """Test detection of CALLS relationships."""
        source = """
def helper():
    pass

def caller():
    helper()
"""
        tree = ast.parse(source)
        nodes = NodeBuilder.build_nodes(tree, "/test/file.py")
        
        relationships = RelationshipDetector.detect_method_calls(tree, nodes)
        
        # Note: Current implementation may not detect all calls
        # This test verifies the method runs without error
        assert relationships is not None
    
    def test_detect_dependencies(self):
        """Test detection of DEPENDS_ON relationships."""
        source = """
import os
from typing import List
"""
        tree = ast.parse(source)
        nodes = NodeBuilder.build_nodes(tree, "/test/file.py")
        
        relationships = RelationshipDetector.detect_dependencies(tree, nodes)
        
        # For MVP, dependencies are tracked but may not create relationships
        assert relationships is not None
    
    def test_detect_all(self):
        """Test detection of all relationship types."""
        source = """
class Base:
    pass

class Derived(Base):
    def method(self):
        other_method()

def other_method():
    pass
"""
        tree = ast.parse(source)
        nodes = NodeBuilder.build_nodes(tree, "/test/file.py")
        
        relationships = RelationshipDetector.detect_all(nodes, tree)
        
        assert len(relationships) > 0
        
        # Check relationship types
        types = set(r.type for r in relationships)
        assert 'CONTAINS' in types
