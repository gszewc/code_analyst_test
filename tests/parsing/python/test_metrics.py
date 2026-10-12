"""Tests for MetricsCollector component."""

import time
import pytest

from codeminer.parsing.python.metrics import MetricsCollector
from codeminer.parsing.models import ASTNode, Relationship, ParseError, NodeType


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def test_metrics_collector_start_stop(self):
        """Test starting and stopping metrics collection."""
        collector = MetricsCollector()
        start_time = time.perf_counter()
        
        time.sleep(0.01)  # Small delay
        
        summary = collector.stop(
            start_time,
            total_files=1,
            nodes=[],
            relationships=[],
            errors=[]
        )
        
        assert summary.parsing_duration_ms >= 0
        assert summary.total_files == 1
    
    def test_metrics_collector_record_file(self):
        """Test recording file count."""
        collector = MetricsCollector()
        
        collector.record_file()
        collector.record_file()
        collector.record_file()
        
        assert collector.files_parsed == 3
    
    def test_metrics_collector_record_node(self):
        """Test recording node count."""
        collector = MetricsCollector()
        
        collector.record_node('Class')
        collector.record_node('Method')
        collector.record_node('Method')
        
        assert collector.nodes_created == 3
    
    def test_metrics_collector_summary(self):
        """Test summary generation with nodes and relationships."""
        collector = MetricsCollector()
        start_time = time.perf_counter()
        
        # Create test nodes
        nodes = [
            ASTNode(
                id="1",
                type="File",
                name="test.py",
                source_file="test.py",
                start_line=1,
                end_line=10
            ),
            ASTNode(
                id="2",
                type="Class",
                name="MyClass",
                source_file="test.py",
                start_line=2,
                end_line=8
            ),
            ASTNode(
                id="3",
                type="Method",
                name="my_method",
                source_file="test.py",
                start_line=3,
                end_line=7
            ),
        ]
        
        # Create test relationships
        relationships = [
            Relationship(source_id="1", target_id="2", type="CONTAINS"),
            Relationship(source_id="2", target_id="3", type="CONTAINS"),
        ]
        
        summary = collector.stop(
            start_time,
            total_files=1,
            nodes=nodes,
            relationships=relationships,
            errors=[]
        )
        
        assert summary.total_files == 1
        assert summary.total_nodes == 3
        assert summary.total_relationships == 2
        assert 'File' in summary.nodes_by_type
        assert 'Class' in summary.nodes_by_type
        assert 'Method' in summary.nodes_by_type
        assert 'CONTAINS' in summary.relationships_by_type
    
    def test_metrics_collector_with_errors(self):
        """Test summary includes error count."""
        collector = MetricsCollector()
        start_time = time.perf_counter()
        
        errors = [
            ParseError(file_path="test.py", message="Error 1"),
            ParseError(file_path="test.py", message="Error 2"),
        ]
        
        summary = collector.stop(
            start_time,
            total_files=1,
            nodes=[],
            relationships=[],
            errors=errors
        )
        
        assert summary.total_errors == 2
