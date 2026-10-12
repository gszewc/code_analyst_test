"""Tests for orchestrator node/relationship filtering logic."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from codeminer.components.analysis_orchestrator import AnalysisOrchestrator
from codeminer.parsing.models import ASTResult, ASTNode, Relationship, FileInfo, Summary


def make_node(node_id: str, node_type: str, name: str) -> ASTNode:
    return ASTNode(
        id=node_id, type=node_type, name=name,
        source_file="test.py", start_line=1, end_line=1,
    )


def make_relationship(source_id: str, target_id: str, rel_type: str) -> Relationship:
    return Relationship(source_id=source_id, target_id=target_id, type=rel_type)


def make_ast_result(nodes, relationships) -> ASTResult:
    return ASTResult(
        file_info=FileInfo(path="/test", name="test", is_directory=True, file_count=1),
        nodes=nodes,
        relationships=relationships,
        summary=Summary(total_files=1, total_nodes=len(nodes), total_relationships=len(relationships)),
    )


class TestFilterASTResult:
    """Test the filtering logic that runs before storage."""

    def test_filter_nodes_by_type(self):
        """Only enabled node types should survive filtering."""
        nodes = [
            make_node("1", "File", "test.py"),
            make_node("2", "Class", "Foo"),
            make_node("3", "Variable", "x"),
        ]
        rels = [
            make_relationship("1", "2", "CONTAINS"),
            make_relationship("2", "3", "CONTAINS"),
        ]
        result = make_ast_result(nodes, rels)

        filtered = AnalysisOrchestrator.filter_ast_result(
            result,
            enabled_node_types=["File", "Class"],
            enabled_relationship_types=["CONTAINS"],
        )

        assert len(filtered.nodes) == 2
        assert {n.type for n in filtered.nodes} == {"File", "Class"}

    def test_filter_relationships_by_type(self):
        """Only enabled relationship types should survive filtering."""
        nodes = [
            make_node("1", "File", "test.py"),
            make_node("2", "Class", "Foo"),
            make_node("3", "Class", "Bar"),
        ]
        rels = [
            make_relationship("1", "2", "CONTAINS"),
            make_relationship("2", "3", "EXTENDS"),
        ]
        result = make_ast_result(nodes, rels)

        filtered = AnalysisOrchestrator.filter_ast_result(
            result,
            enabled_node_types=["File", "Class"],
            enabled_relationship_types=["CONTAINS"],
        )

        assert len(filtered.relationships) == 1
        assert filtered.relationships[0].type == "CONTAINS"

    def test_orphaned_relationships_removed(self):
        """Relationships referencing filtered-out nodes should be dropped."""
        nodes = [
            make_node("1", "File", "test.py"),
            make_node("2", "Class", "Foo"),
            make_node("3", "Variable", "x"),
        ]
        rels = [
            make_relationship("1", "2", "CONTAINS"),
            make_relationship("2", "3", "CONTAINS"),  # target node filtered out
        ]
        result = make_ast_result(nodes, rels)

        filtered = AnalysisOrchestrator.filter_ast_result(
            result,
            enabled_node_types=["File", "Class"],
            enabled_relationship_types=["CONTAINS"],
        )

        assert len(filtered.relationships) == 1
        assert filtered.relationships[0].target_id == "2"

    def test_none_means_all(self):
        """None for enabled types should keep everything."""
        nodes = [
            make_node("1", "File", "test.py"),
            make_node("2", "Variable", "x"),
        ]
        rels = [make_relationship("1", "2", "CONTAINS")]
        result = make_ast_result(nodes, rels)

        filtered = AnalysisOrchestrator.filter_ast_result(
            result,
            enabled_node_types=None,
            enabled_relationship_types=None,
        )

        assert len(filtered.nodes) == 2
        assert len(filtered.relationships) == 1


class TestOrchestratorDeletion:
    """Test that orchestrator calls delete_by_project when flagged."""

    @pytest.mark.asyncio
    async def test_delete_graph_data_before_parsing(self):
        """When delete_graph_data=True, orchestrator should delete before parsing."""
        graph_storage = MagicMock()
        analysis_storage = MagicMock()
        project_storage = MagicMock()

        orchestrator = AnalysisOrchestrator(
            parser_registry=MagicMock(),
            file_discovery=MagicMock(),
            graph_storage=graph_storage,
            project_storage=project_storage,
            analysis_storage=analysis_storage,
        )

        # Mock internal methods
        result = make_ast_result(
            [make_node("1", "File", "test.py")],
            [],
        )
        orchestrator._parse_directory = AsyncMock(return_value=result)
        orchestrator._store_ast_result = AsyncMock()
        orchestrator._update_progress = AsyncMock()

        project_id = uuid4()
        job_id = uuid4()

        await orchestrator.orchestrate_analysis_for_directory(
            project_id=project_id,
            job_id=job_id,
            project_path="/test",
            file_paths=["test.py"],
            delete_graph_data=True,
        )

        graph_storage.delete_by_project.assert_called_once_with(str(project_id))

    @pytest.mark.asyncio
    async def test_no_delete_when_flag_false(self):
        """When delete_graph_data=False, orchestrator should not delete."""
        graph_storage = MagicMock()
        analysis_storage = MagicMock()
        project_storage = MagicMock()

        orchestrator = AnalysisOrchestrator(
            parser_registry=MagicMock(),
            file_discovery=MagicMock(),
            graph_storage=graph_storage,
            project_storage=project_storage,
            analysis_storage=analysis_storage,
        )

        result = make_ast_result(
            [make_node("1", "File", "test.py")],
            [],
        )
        orchestrator._parse_directory = AsyncMock(return_value=result)
        orchestrator._store_ast_result = AsyncMock()
        orchestrator._update_progress = AsyncMock()

        await orchestrator.orchestrate_analysis_for_directory(
            project_id=uuid4(),
            job_id=uuid4(),
            project_path="/test",
            file_paths=["test.py"],
            delete_graph_data=False,
        )

        graph_storage.delete_by_project.assert_not_called()
