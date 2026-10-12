"""Tests for AnalysisOrchestrator map generation behaviour."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from codeminer.components.analysis_orchestrator import AnalysisOrchestrator
from codeminer.parsing.models import ASTResult, ASTNode, Relationship, FileInfo, Summary


def make_node(node_id, node_type, name, source_file="test.py"):
    return ASTNode(
        id=node_id, type=node_type, name=name,
        source_file=source_file, start_line=1, end_line=1,
    )


def make_ast_result(nodes):
    return ASTResult(
        file_info=FileInfo(path="/test", name="test", is_directory=True, file_count=1),
        nodes=nodes,
        relationships=[],
        summary=Summary(total_files=1, total_nodes=len(nodes)),
    )


def make_orchestrator(repo_map_generator=None):
    return AnalysisOrchestrator(
        parser_registry=MagicMock(),
        file_discovery=MagicMock(),
        graph_storage=MagicMock(),
        project_storage=MagicMock(),
        analysis_storage=MagicMock(),
        repo_map_generator=repo_map_generator,
    )


class TestOrchestratorGenerateMap:
    @pytest.mark.asyncio
    async def test_generate_map_true_calls_generator(self, tmp_path):
        """When generate_map=True, RepoMapGenerator.generate is called."""
        repo_map_generator = MagicMock()
        orchestrator = make_orchestrator(repo_map_generator)

        nodes = [make_node("1", "Class", "Foo")]
        result = make_ast_result(nodes)

        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = result
        mock_parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = mock_parser
        orchestrator.file_discovery.discover_files.return_value = {"python": ["test.py"]}

        orchestrator.analysis_storage.start_job = MagicMock()
        orchestrator.analysis_storage.complete_job = MagicMock()
        orchestrator.analysis_storage.update_progress = MagicMock()
        orchestrator.graph_storage.store_ast_result = MagicMock()

        project_id = uuid4()
        job_id = uuid4()

        await orchestrator.orchestrate_analysis_for_directory(
            project_id=project_id,
            job_id=job_id,
            project_path=str(tmp_path),
            project_source_root=str(tmp_path),
            generate_map=True,
        )

        repo_map_generator.generate.assert_called_once()
        call_args = repo_map_generator.generate.call_args
        passed_nodes = call_args[0][0]
        assert any(n.name == "Foo" for n in passed_nodes)
        passed_path = call_args[0][1]
        assert passed_path == tmp_path / "repomap.txt"

    @pytest.mark.asyncio
    async def test_generate_map_false_does_not_call_generator(self, tmp_path):
        """When generate_map=False (default), generator is not called."""
        repo_map_generator = MagicMock()
        orchestrator = make_orchestrator(repo_map_generator)

        result = make_ast_result([make_node("1", "Class", "Foo")])
        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = result
        mock_parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = mock_parser
        orchestrator.file_discovery.discover_files.return_value = {"python": ["test.py"]}
        orchestrator.analysis_storage.start_job = MagicMock()
        orchestrator.analysis_storage.complete_job = MagicMock()
        orchestrator.analysis_storage.update_progress = MagicMock()
        orchestrator.graph_storage.store_ast_result = MagicMock()

        await orchestrator.orchestrate_analysis_for_directory(
            project_id=uuid4(),
            job_id=uuid4(),
            project_path=str(tmp_path),
            project_source_root=str(tmp_path),
            generate_map=False,
        )

        repo_map_generator.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_map_for_directory_no_graph_storage(self, tmp_path):
        """generate_map_for_directory does not call graph_storage.store_ast_result."""
        repo_map_generator = MagicMock()
        orchestrator = make_orchestrator(repo_map_generator)

        result = make_ast_result([make_node("1", "Class", "Bar")])
        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = result
        mock_parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = mock_parser
        orchestrator.file_discovery.discover_files.return_value = {"python": ["test.py"]}

        output_path = tmp_path / "repomap.txt"
        await orchestrator.generate_map_for_directory(
            project_path=str(tmp_path),
            output_path=output_path,
            project_source_root=str(tmp_path),
        )

        orchestrator.graph_storage.store_ast_result.assert_not_called()
        repo_map_generator.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_map_for_directory_no_job_tracking(self, tmp_path):
        """generate_map_for_directory does not interact with analysis_storage."""
        repo_map_generator = MagicMock()
        orchestrator = make_orchestrator(repo_map_generator)

        result = make_ast_result([make_node("1", "Function", "f")])
        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = result
        mock_parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = mock_parser
        orchestrator.file_discovery.discover_files.return_value = {"python": ["test.py"]}

        await orchestrator.generate_map_for_directory(
            project_path=str(tmp_path),
            output_path=tmp_path / "repomap.txt",
            project_source_root=str(tmp_path),
        )

        orchestrator.analysis_storage.start_job.assert_not_called()
        orchestrator.analysis_storage.complete_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_project_skips_language_with_no_registered_parser(self, tmp_path):
        """Languages returned by file_discovery with no parser are silently skipped."""
        repo_map_generator = MagicMock()
        orchestrator = make_orchestrator(repo_map_generator)

        # discover_files returns two languages, but no parser is registered for "ruby"
        orchestrator.file_discovery.discover_files.return_value = {
            "python": ["a.py"],
            "ruby": ["b.rb"],
        }
        result = make_ast_result([make_node("1", "Class", "Foo")])
        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = result
        mock_parser.create_cross_file_resolver.return_value = None

        def get_parser(language):
            return mock_parser if language == "python" else None

        orchestrator.parser_registry.get_parser_for_language.side_effect = get_parser
        orchestrator.analysis_storage.start_job = MagicMock()
        orchestrator.analysis_storage.complete_job = MagicMock()
        orchestrator.analysis_storage.update_progress = MagicMock()
        orchestrator.graph_storage.store_ast_result = MagicMock()

        # Should not raise; ruby is silently skipped
        await orchestrator.orchestrate_analysis_for_directory(
            project_id=uuid4(),
            job_id=uuid4(),
            project_path=str(tmp_path),
            project_source_root=str(tmp_path),
        )

        # parse_files only called once (for python), not for ruby
        assert mock_parser.parse_files.call_count == 1

    @pytest.mark.asyncio
    async def test_parse_project_skips_language_when_parse_returns_none(self, tmp_path):
        """When parse_files returns None for a language, that language is silently skipped."""
        repo_map_generator = MagicMock()
        orchestrator = make_orchestrator(repo_map_generator)

        orchestrator.file_discovery.discover_files.return_value = {"python": ["a.py"]}
        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = None  # parser returns None
        orchestrator.parser_registry.get_parser_for_language.return_value = mock_parser
        orchestrator.analysis_storage.start_job = MagicMock()
        orchestrator.analysis_storage.complete_job = MagicMock()
        orchestrator.analysis_storage.update_progress = MagicMock()
        orchestrator.graph_storage.store_ast_result = MagicMock()

        # Should not raise; None result is silently skipped
        await orchestrator.orchestrate_analysis_for_directory(
            project_id=uuid4(),
            job_id=uuid4(),
            project_path=str(tmp_path),
            project_source_root=str(tmp_path),
        )

        orchestrator.graph_storage.store_ast_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_map_for_directory_with_no_generator_does_not_raise(self, tmp_path):
        """When repo_map_generator is None, generate_map_for_directory returns without error."""
        orchestrator = make_orchestrator(repo_map_generator=None)

        result = make_ast_result([make_node("1", "Class", "Foo")])
        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = result
        mock_parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = mock_parser
        orchestrator.file_discovery.discover_files.return_value = {"python": ["test.py"]}

        # Should not raise
        await orchestrator.generate_map_for_directory(
            project_path=str(tmp_path),
            output_path=tmp_path / "repomap.txt",
            project_source_root=str(tmp_path),
        )
        # No assertion needed — method returning without error is the requirement

    @pytest.mark.asyncio
    async def test_generate_map_for_directory_passes_correct_output_path(self, tmp_path):
        """generate_map_for_directory passes the specified output_path to the generator."""
        repo_map_generator = MagicMock()
        orchestrator = make_orchestrator(repo_map_generator)

        result = make_ast_result([make_node("1", "Class", "Bar")])
        mock_parser = MagicMock()
        mock_parser.parse_files.return_value = result
        mock_parser.create_cross_file_resolver.return_value = None
        orchestrator.parser_registry.get_parser_for_language.return_value = mock_parser
        orchestrator.file_discovery.discover_files.return_value = {"python": ["test.py"]}

        expected_path = tmp_path / "custom_repomap.txt"
        await orchestrator.generate_map_for_directory(
            project_path=str(tmp_path),
            output_path=expected_path,
            project_source_root=str(tmp_path),
        )

        call_args = repo_map_generator.generate.call_args
        assert call_args[0][1] == expected_path
