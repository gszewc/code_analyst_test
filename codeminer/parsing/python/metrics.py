"""
Metrics collector for AST Parser.

Re-exports from codeminer.parsing.metrics for backwards compatibility.
"""

from codeminer.parsing.metrics import MetricsCollector, Summary

__all__ = ["MetricsCollector", "Summary"]
