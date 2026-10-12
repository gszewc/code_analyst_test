"""Symlink and alias-path regression tests for AnalysisOrchestrator."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from codeminer.components.analysis_orchestrator import AnalysisOrchestrator
from codeminer.parsing.models import ASTNode, ASTResult


class TestOrchestratorSymlinkAliasPaths:
    """Verify alias-path identity is preserved through orchestration."""

    @staticmethod
    def _make_orchestrator() -> AnalysisOrchestrator:
        return AnalysisOrchestrator(
            parser_registry=MagicMock(),
            file_discovery=MagicMock(),
            graph_storage=MagicMock(),
            project_storage=MagicMock(),
            analysis_storage=MagicMock(),
        )

    @staticmethod
    def _make_alias_result() -> ASTResult:
        return ASTResult(
            nodes=[
                ASTNode(
                    id="node-alias-a",
                    type="File",
                    name="shared.py",
                    source_file="linked_a/shared.py",
                    start_line=1,
                    end_line=20,
                ),
                ASTNode(
                    id="node-alias-b",
                    type="File",
                    name="shared.py",
                    source_file="linked_b/shared.py",
                    start_line=1,
                    end_line=20,
                ),
            ]
        )

    @pytest.mark.asyncio
    async def test_parse_project_preserves_alias_discovery_inputs(self):
        """The parser should receive discovery outputs as-is, with alias paths intact."""
        orchestrator = self._make_orchestrator()

        alias_files = ["source/linked_a/shared.py", "source/linked_b/shared.py"]
        orchestrator.file_discovery.discover_files.return_value = {"python": alias_files}

        parser = MagicMock()
        parser.parse_files.return_value = ASTResult(nodes=[])
        parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = parser

        _, total_files = await orchestrator._parse_project(
            project_path="source",
            project_source_root="source",
        )

        parser.parse_files.assert_called_once_with(alias_files, "source")
        assert total_files == 2

    @pytest.mark.asyncio
    async def test_orchestration_keeps_distinct_alias_nodes_for_same_logical_file(self):
        """Nodes discovered through different alias paths should not be deduplicated."""
        orchestrator = self._make_orchestrator()

        parser = MagicMock()
        parser.parse_files.return_value = self._make_alias_result()
        parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = parser

        orchestrator.file_discovery.discover_files.return_value = {
            "python": ["source/linked_a/shared.py", "source/linked_b/shared.py"]
        }

        await orchestrator.orchestrate_analysis_for_directory(
            project_id=uuid4(),
            job_id=uuid4(),
            project_path="source",
            project_source_root="source",
        )

        orchestrator.graph_storage.store_ast_result.assert_called_once()
        stored_result = orchestrator.graph_storage.store_ast_result.call_args[0][1]
        source_files = [node.source_file for node in stored_result.nodes]

        assert source_files.count("linked_a/shared.py") == 1
        assert source_files.count("linked_b/shared.py") == 1
