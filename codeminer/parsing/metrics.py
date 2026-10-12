"""
Metrics collector for AST Parser.

This module collects parsing metrics and generates summary statistics.
"""

import time
from typing import List

from codeminer.parsing.models import ASTNode, Relationship, ParseError, Summary


class MetricsCollector:
    """Collect parsing metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.files_parsed = 0
        self.nodes_created = 0
        self.relationships_created = 0
        self.errors_count = 0
        self.start_time: float = None

    def start(self):
        """Start timing."""
        self.start_time = time.perf_counter()

    def stop(
        self,
        start_time: float,
        total_files: int,
        nodes: List[ASTNode],
        relationships: List[Relationship],
        errors: List[ParseError],
    ) -> Summary:
        """
        Stop timing and return summary.

        Args:
            start_time: Start time from perf_counter()
            total_files: Total files parsed
            nodes: List of nodes created
            relationships: List of relationships created
            errors: List of errors encountered

        Returns:
            Summary statistics
        """
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Count nodes by type
        nodes_by_type = {}
        for node in nodes:
            node_type = node.type
            nodes_by_type[node_type] = nodes_by_type.get(node_type, 0) + 1

        # Count relationships by type
        relationships_by_type = {}
        for rel in relationships:
            rel_type = rel.type
            relationships_by_type[rel_type] = relationships_by_type.get(rel_type, 0) + 1

        return Summary(
            total_files=total_files,
            total_nodes=len(nodes),
            nodes_by_type=nodes_by_type,
            total_relationships=len(relationships),
            relationships_by_type=relationships_by_type,
            total_errors=len(errors),
            parsing_duration_ms=duration_ms,
        )

    def record_file(self):
        """Record a file parsed."""
        self.files_parsed += 1

    def record_node(self, node_type: str):
        """
        Record a node created.

        Args:
            node_type: Type of node created
        """
        self.nodes_created += 1

    def record_relationship(self, rel_type: str):
        """
        Record a relationship created.

        Args:
            rel_type: Type of relationship
        """
        self.relationships_created += 1

    def record_error(self):
        """Record an error."""
        self.errors_count += 1
