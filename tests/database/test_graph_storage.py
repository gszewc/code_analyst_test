"""
Tests for GraphStorage - Neo4j AST graph operations.

Note: These tests use mocks since Neo4j may not be available in test environment.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime  # noqa: F401 – kept for downstream compatibility

from codeminer.database.graph_storage import GraphStorage, GraphStorageError
from codeminer.database.models import StorageResult, GraphSummary
from codeminer.parsing.models import (
    ASTResult,
    ASTNode,
    Relationship,
    NodeType,  # noqa: F401 – kept for downstream compatibility
    FileInfo,
)


class TestGraphStorage:
    """Tests for GraphStorage."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        """Create GraphStorage instance."""
        return GraphStorage(neo4j_manager_mock)

    @pytest.fixture
    def sample_ast_result(self) -> ASTResult:
        """Create sample AST result for testing."""
        return ASTResult(
            file_info=FileInfo(
                path="/test/file.py", name="file.py", size=1000, language="python"
            ),
            nodes=[
                ASTNode(
                    id="node-1",
                    type="File",
                    name="file.py",
                    source_file="/test/file.py",
                    start_line=1,
                    end_line=100,
                ),
                ASTNode(
                    id="node-2",
                    type="Class",
                    name="TestClass",
                    source_file="/test/file.py",
                    start_line=10,
                    end_line=50,
                    base_classes=["object"],
                ),
                ASTNode(
                    id="node-3",
                    type="Method",
                    name="test_method",
                    source_file="/test/file.py",
                    start_line=15,
                    end_line=25,
                ),
            ],
            relationships=[
                Relationship(source_id="node-1", target_id="node-2", type="CONTAINS"),
                Relationship(source_id="node-2", target_id="node-3", type="CONTAINS"),
            ],
        )

    @patch.object(GraphStorage, "_store_node_batch", return_value=3)
    @patch.object(GraphStorage, "_store_relationships", return_value=2)
    def test_store_ast_result(
        self,
        mock_store_rels,
        mock_store_nodes,
        storage,
        sample_ast_result,
        neo4j_manager_mock,
    ):
        """Test storing AST result."""
        # Setup mock transaction
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        result = storage.store_ast_result("project-id", sample_ast_result)

        assert isinstance(result, StorageResult)
        assert result.files_stored == 1
        assert result.nodes_stored == 3
        assert result.relationships_stored == 2
        assert result.duration_ms >= 0

    def test_store_ast_result_empty(self, storage, neo4j_manager_mock):
        """Test storing empty AST result."""
        empty_result = ASTResult(
            file_info=FileInfo(path="/test/empty.py", name="empty.py"),
            nodes=[],
            relationships=[],
        )

        mock_tx = MagicMock()
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        result = storage.store_ast_result("project-id", empty_result)

        assert result.nodes_stored == 0
        assert result.relationships_stored == 0

    def test_store_ast_result_error(
        self, storage, sample_ast_result, neo4j_manager_mock
    ):
        """Test storing AST result with error raises GraphStorageError."""
        mock_tx = MagicMock()
        mock_tx.run.side_effect = Exception("Test error")
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        with pytest.raises(GraphStorageError):
            storage.store_ast_result("project-id", sample_ast_result)

    def test_query_nodes_by_type(self, storage, neo4j_manager_mock):
        """Test querying nodes by type."""
        # Setup mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [{"node": {"id": "node-1", "type": "Class", "name": "TestClass"}}]
            )
        )
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        nodes = storage.query_nodes_by_type("project-id", "Class")

        assert len(nodes) == 1
        assert nodes[0]["type"] == "Class"

    def test_query_nodes_by_project(self, storage, neo4j_manager_mock):
        """Test querying nodes by project."""
        # Setup mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    {"node": {"id": "node-1", "type": "Class"}},
                    {"node": {"id": "node-2", "type": "Method"}},
                ]
            )
        )
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        nodes = storage.query_nodes_by_project("project-id")

        assert len(nodes) == 2

    def test_query_relationships(self, storage, neo4j_manager_mock):
        """Test querying relationships."""
        # Setup mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    {
                        "relationship": {
                            "source_id": "node-1",
                            "target_id": "node-2",
                            "type": "CONTAINS",
                            "source": {"id": "node-1", "type": "File"},
                            "target": {"id": "node-2", "type": "Class"},
                        }
                    }
                ]
            )
        )
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        relationships = storage.query_relationships("project-id")

        assert len(relationships) == 1
        assert relationships[0]["type"] == "CONTAINS"

    def test_query_relationships_by_type(self, storage, neo4j_manager_mock):
        """Test querying relationships by type."""
        # Setup mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter([{"relationship": {"type": "CONTAINS"}}])
        )
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        relationships = storage.query_relationships(
            "project-id", relationship_type="CONTAINS"
        )

        assert len(relationships) == 1

    def test_get_node_by_id(self, storage, neo4j_manager_mock):
        """Test retrieving a node by project and id."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"node": {"id": "node-1", "type": "Class"}}
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        node = storage.get_node_by_id("project-id", "node-1")

        assert node is not None
        assert node["id"] == "node-1"

    def test_get_node_by_id_not_found(self, storage, neo4j_manager_mock):
        """Test retrieving missing node returns None."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        node = storage.get_node_by_id("project-id", "missing")

        assert node is None

    def test_search_nodes(self, storage, neo4j_manager_mock):
        """Test searching nodes by name."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    {"node": {"id": "node-1", "name": "Function1", "type": "Function"}},
                    {"node": {"id": "node-2", "name": "Function2", "type": "Function"}},
                ]
            )
        )
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        nodes = storage.search_nodes(
            "project-id", "Function", node_type="Function", limit=10
        )

        assert len(nodes) == 2
        assert nodes[0]["type"] == "Function"

    def test_get_relationships_for_node(self, storage, neo4j_manager_mock):
        """Test retrieving node relationships with direction."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    {
                        "relationship": {
                            "source_id": "node-1",
                            "target_id": "node-2",
                            "type": "CALLS",
                        }
                    },
                    {"relationship": None},
                ]
            )
        )
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        relationships = storage.get_relationships_for_node(
            "project-id", "node-1", direction="both"
        )

        assert len(relationships) == 1
        assert relationships[0]["type"] == "CALLS"

    def test_get_node_count(self, storage, neo4j_manager_mock):
        """Test node count lookup."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"count": 42}
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        count = storage.get_node_count("project-id")

        assert count == 42

    def test_get_relationship_count(self, storage, neo4j_manager_mock):
        """Test relationship count lookup."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"count": 17}
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        count = storage.get_relationship_count("project-id")

        assert count == 17

    def test_get_summary(self, storage, neo4j_manager_mock):
        """Test getting graph summary."""
        # Setup mock session
        mock_session = MagicMock()

        # Mock node count result
        mock_node_result = MagicMock()
        mock_node_result.__iter__ = Mock(
            return_value=iter(
                [{"type": "Class", "count": 5}, {"type": "Method", "count": 10}]
            )
        )

        # Mock relationship count result
        mock_rel_result = MagicMock()
        mock_rel_result.__iter__ = Mock(
            return_value=iter(
                [{"type": "CONTAINS", "count": 8}, {"type": "CALLS", "count": 3}]
            )
        )

        mock_session.run.side_effect = [mock_node_result, mock_rel_result]
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        summary = storage.get_summary("project-id")

        assert isinstance(summary, GraphSummary)
        assert summary.total_nodes == 15
        assert summary.nodes_by_type == {"Class": 5, "Method": 10}
        assert summary.total_relationships == 11
        assert summary.relationships_by_type == {"CONTAINS": 8, "CALLS": 3}

    def test_delete_by_project(self, storage, neo4j_manager_mock):
        """Test deleting graph data by project."""
        mock_tx = MagicMock()

        mock_rel_result = MagicMock()
        mock_rel_result.single.return_value = {"deleted_count": 5}

        mock_node_result = MagicMock()
        mock_node_result.single.return_value = {"deleted_count": 10}

        mock_tx.run.side_effect = [mock_rel_result, mock_node_result]
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        deleted_count = storage.delete_by_project("project-id")

        assert deleted_count == 15  # 10 nodes + 5 relationships

    def test_delete_all(self, storage, neo4j_manager_mock):
        """Test deleting all graph data."""
        mock_session = MagicMock()

        mock_rel_result = MagicMock()
        mock_rel_result.single.return_value = {"deleted_count": 4}

        mock_node_result = MagicMock()
        mock_node_result.single.return_value = {"deleted_count": 9}

        mock_session.run.side_effect = [mock_rel_result, mock_node_result]
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )

        deleted_count = storage.delete_all()

        assert deleted_count == 13

    def test_node_to_params_preserves_relative_source_file(self, storage):
        """Relative source_file should be passed to Neo4j unchanged."""
        node = ASTNode(
            id="node-relative-1",
            type="File",
            name="app.py",
            source_file="application/app.py",
            start_line=1,
            end_line=10,
        )

        params = storage._node_to_params(node, "project-id")

        assert params["source_file"] == "application/app.py"

    def test_node_to_params(self, storage):
        """Test converting ASTNode to Cypher parameters."""
        node = ASTNode(
            id="test-id",
            type="Class",
            name="TestClass",
            source_file="/test.py",
            start_line=10,
            end_line=20,
            base_classes=["object"],
            decorators=["@pytest.fixture"],
        )

        params = storage._node_to_params(node, "project-id")

        assert params["id"] == "test-id"
        assert params["type"] == "Class"
        assert params["name"] == "TestClass"
        assert params["project_id"] == "project-id"
        assert params["base_classes"] == ["object"]
        assert params["decorators"] == ["@pytest.fixture"]

    def test_store_node_batch(self, storage, neo4j_manager_mock):
        """Test _store_node_batch uses UNWIND — one tx.run call per label group."""
        mock_session = MagicMock()
        mock_session.run.return_value = MagicMock()

        nodes = [
            ASTNode(
                id=f"node-{i}", type="Class", name=f"Class{i}", source_file="/test.py"
            )
            for i in range(5)
        ]

        count = storage._store_node_batch(mock_session, "project-id", nodes)

        assert count == 5
        # All 5 Class nodes are in one label group → 1 UNWIND call (batch_size 500 > 5)
        assert mock_session.run.call_count == 1

    def test_store_relationships(self, storage, neo4j_manager_mock):
        """Test _store_relationships uses UNWIND — one tx.run call per rel type."""
        mock_session = MagicMock()
        mock_session.run.return_value = MagicMock()

        relationships = [
            Relationship(source_id="node-1", target_id="node-2", type="CONTAINS")
            for _ in range(3)
        ]

        # stored_node_ids includes both endpoints so no orphans
        stored, orphans = storage._store_relationships(
            mock_session,
            "project-id",
            relationships,
            stored_node_ids={"node-1", "node-2"},
        )

        assert stored == 3
        assert orphans == 0

    def test_store_ast_result_uses_transaction(
        self, storage, neo4j_manager_mock, sample_ast_result
    ):
        """store_ast_result must call transaction(), not get_session()."""
        mock_tx = MagicMock()
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        storage.store_ast_result("project-id", sample_ast_result)

        neo4j_manager_mock.transaction.assert_called_once()
        neo4j_manager_mock.get_session.assert_not_called()

    def test_store_ast_result_node_failure_raises_graph_storage_error(
        self, storage, neo4j_manager_mock, sample_ast_result
    ):
        """A node write failure propagates as GraphStorageError (no silent partial write)."""
        mock_tx = MagicMock()
        mock_tx.run.side_effect = Exception("Cypher error")
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        with pytest.raises(GraphStorageError):
            storage.store_ast_result("project-id", sample_ast_result)

    def test_store_node_batch_propagates_cypher_error(self, storage):
        """A Cypher error in _store_node_batch must propagate, not be swallowed."""
        from neo4j.exceptions import CypherSyntaxError

        mock_tx = MagicMock()
        mock_tx.run.side_effect = CypherSyntaxError(None, "bad cypher")

        nodes = [ASTNode(id="node-1", type="Class", name="Cls", source_file="/f.py")]

        with pytest.raises(CypherSyntaxError):
            storage._store_node_batch(mock_tx, "proj", nodes)

    def test_delete_nodes_by_project(self, storage, neo4j_manager_mock):
        """Test deleting nodes by project."""
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"deleted_count": 10}
        mock_tx.run.return_value = mock_result
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        deleted_count = storage.delete_nodes_by_project("project-id")

        assert deleted_count == 10
        mock_tx.run.assert_called_once()

    def test_delete_relationships_by_project(self, storage, neo4j_manager_mock):
        """Test deleting relationships by project."""
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"deleted_count": 5}
        mock_tx.run.return_value = mock_result
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        deleted_count = storage.delete_relationships_by_project("project-id")

        assert deleted_count == 5
        mock_tx.run.assert_called_once()

    def test_delete_nodes_by_type(self, storage, neo4j_manager_mock):
        """Test deleting nodes by type."""
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"deleted_count": 7}
        mock_tx.run.return_value = mock_result
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        deleted_count = storage.delete_nodes_by_type(
            "project-id", node_types=["Method", "Function"]
        )

        assert deleted_count == 7
        mock_tx.run.assert_called_once()

    def test_delete_nodes_by_type_all(self, storage, neo4j_manager_mock):
        """Test deleting all nodes by type (no type filter)."""
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"deleted_count": 15}
        mock_tx.run.return_value = mock_result
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        deleted_count = storage.delete_nodes_by_type("project-id", node_types=None)

        assert deleted_count == 15

    def test_delete_relationships_by_type(self, storage, neo4j_manager_mock):
        """Test deleting relationships by type."""
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"deleted_count": 3}
        mock_tx.run.return_value = mock_result
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        deleted_count = storage.delete_relationships_by_type(
            "project-id", relationship_types=["CALLS", "DEPENDS_ON"]
        )

        assert deleted_count == 3
        mock_tx.run.assert_called_once()

    def test_delete_relationships_by_type_all(self, storage, neo4j_manager_mock):
        """Test deleting all relationships by type (no type filter)."""
        mock_tx = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"deleted_count": 20}
        mock_tx.run.return_value = mock_result
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        deleted_count = storage.delete_relationships_by_type(
            "project-id", relationship_types=None
        )

        assert deleted_count == 20


class TestGraphStorageError:
    """Tests for GraphStorageError."""

    def test_exception_creation(self):
        """Test creating GraphStorageError."""
        error = GraphStorageError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inheritance(self):
        """Test GraphStorageError inherits from Exception."""
        error = GraphStorageError("Test")
        assert isinstance(error, Exception)

    def test_exception_extended_fields(self):
        """GraphStorageError exposes error_code, batch_id, attempt_details."""
        error = GraphStorageError(
            "batch failed",
            error_code="BATCH_WRITE_ERROR",
            batch_id="batch-1",
            attempt_details="3 retries",
            failure_policy_applied=True,
        )
        assert error.error_code == "BATCH_WRITE_ERROR"
        assert error.batch_id == "batch-1"
        assert error.attempt_details == "3 retries"
        assert error.failure_policy_applied is True


# ---------------------------------------------------------------------------
# TestQueryProjectRelationships — US1, US2, US3, US4 storage layer
# (T003, T010, T015, T020, T029)
# ---------------------------------------------------------------------------


def _make_neo4j_relationship(
    source_id: str = "node-1",
    target_id: str = "node-2",
    rel_type: str = "CONTAINS",
    project_id: str = "test-project-id",
) -> dict:
    """Build a minimal Neo4j relationship record fixture."""
    return {
        "source_id": source_id,
        "target_id": target_id,
        "type": rel_type,
        "project_id": project_id,
        "source": {
            "id": source_id,
            "type": "File",
            "name": source_id,
            "source_file": f"{source_id}.py",
        },
        "target": {
            "id": target_id,
            "type": "Class",
            "name": target_id,
            "source_file": f"{target_id}.py",
        },
    }


class TestQueryProjectRelationships:
    """Tests for GraphStorage.query_project_relationships."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def _make_session(self, neo4j_manager_mock, records):
        """Wire up a mock session that returns the given records."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter(records))
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        neo4j_manager_mock.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        return mock_session

    # --- US1: base query path ---

    def test_query_project_relationships_returns_all(self, storage, neo4j_manager_mock):
        """US1: Returns all relationships when types filter is None."""
        records = [
            {"relationship": _make_neo4j_relationship("n1", "n2", "CONTAINS")},
            {"relationship": _make_neo4j_relationship("n2", "n3", "CALLS")},
        ]
        mock_session = self._make_session(neo4j_manager_mock, records)

        result = storage.query_project_relationships("test-project-id")

        assert len(result) == 2
        mock_session.run.assert_called_once()
        call_params = mock_session.run.call_args[0][1]
        assert call_params["types"] == []

    def test_query_project_relationships_empty_project(
        self, storage, neo4j_manager_mock
    ):
        """US1: Returns empty list for project with no relationships."""
        self._make_session(neo4j_manager_mock, [])

        result = storage.query_project_relationships("empty-project-id")

        assert result == []

    # --- US2: type-set filtering ---

    def test_query_project_relationships_single_type_filter(
        self, storage, neo4j_manager_mock
    ):
        """US2: Passes single-element types list to Cypher params."""
        records = [{"relationship": _make_neo4j_relationship("n1", "n2", "CONTAINS")}]
        mock_session = self._make_session(neo4j_manager_mock, records)

        result = storage.query_project_relationships("project-id", types=["CONTAINS"])

        assert len(result) == 1
        call_params = mock_session.run.call_args[0][1]
        assert call_params["types"] == ["CONTAINS"]

    def test_query_project_relationships_multi_type_filter(
        self, storage, neo4j_manager_mock
    ):
        """US2: Passes multi-element types list to Cypher params."""
        records = [
            {"relationship": _make_neo4j_relationship("n1", "n2", "CONTAINS")},
            {"relationship": _make_neo4j_relationship("n2", "n3", "CALLS")},
        ]
        mock_session = self._make_session(neo4j_manager_mock, records)

        result = storage.query_project_relationships(
            "project-id", types=["CONTAINS", "CALLS"]
        )

        assert len(result) == 2
        call_params = mock_session.run.call_args[0][1]
        assert set(call_params["types"]) == {"CONTAINS", "CALLS"}

    def test_query_project_relationships_no_match_type_filter(
        self, storage, neo4j_manager_mock
    ):
        """US4 T029: Non-matching type filter returns empty list."""
        self._make_session(neo4j_manager_mock, [])

        result = storage.query_project_relationships(
            "project-id", types=["NONEXISTENT_TYPE"]
        )

        assert result == []

    # --- US3: limit ---

    def test_query_project_relationships_applies_limit(
        self, storage, neo4j_manager_mock
    ):
        """US3: Passes supplied limit value to Cypher params."""
        records = [{"relationship": _make_neo4j_relationship()}]
        mock_session = self._make_session(neo4j_manager_mock, records)

        storage.query_project_relationships("project-id", limit=25)

        call_params = mock_session.run.call_args[0][1]
        assert call_params["limit"] == 25

    def test_query_project_relationships_default_limit(
        self, storage, neo4j_manager_mock
    ):
        """US3: Uses 1000 as default limit when not specified."""
        mock_session = self._make_session(neo4j_manager_mock, [])

        storage.query_project_relationships("project-id")

        call_params = mock_session.run.call_args[0][1]
        assert call_params["limit"] == 1000

    # --- None relationships are filtered out ---

    def test_query_project_relationships_skips_none_records(
        self, storage, neo4j_manager_mock
    ):
        """Relationship records that are None are excluded from results."""
        records = [
            {"relationship": _make_neo4j_relationship()},
            {"relationship": None},
        ]
        self._make_session(neo4j_manager_mock, records)

        result = storage.query_project_relationships("project-id")

        assert len(result) == 1

    # --- error path ---

    def test_query_project_relationships_raises_on_storage_error(
        self, storage, neo4j_manager_mock
    ):
        """Storage-level exception is wrapped in GraphStorageError."""
        neo4j_manager_mock.get_session.side_effect = Exception("neo4j down")

        with pytest.raises(GraphStorageError):
            storage.query_project_relationships("project-id")


# ---------------------------------------------------------------------------
# UNWIND Batching Tests (T015-T017, T023-T025, T030-T035, T043-T050)
# specs/011-neo4j-unwind-batching
# ---------------------------------------------------------------------------


def _make_ast_node(node_id: str, node_type: str = "Class") -> ASTNode:
    return ASTNode(id=node_id, type=node_type, name=node_id, source_file="/test.py")


def _make_relationship(src: str, tgt: str, rel_type: str = "CONTAINS") -> Relationship:
    return Relationship(source_id=src, target_id=tgt, type=rel_type)


class TestUnwindNodeBatching:
    """T015 – UNWIND batched node writes grouped by label."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_batched_node_writes_with_unwind(self, storage):
        """T015: 1,000 nodes across 3 label types produce exactly 3 UNWIND tx.run calls."""
        mock_tx = MagicMock()

        # 400 File, 400 Class, 200 ASTNode (generic)
        nodes = (
            [_make_ast_node(f"f-{i}", "File") for i in range(400)]
            + [_make_ast_node(f"c-{i}", "Class") for i in range(400)]
            + [_make_ast_node(f"n-{i}", "Method") for i in range(200)]
        )

        count = storage._store_node_batch(mock_tx, "proj", nodes, batch_size=500)

        assert count == 1000
        # 3 label groups with batch_size=500: File(400→1), Class(400→1), Method(200→1)
        assert mock_tx.run.call_count == 3

    def test_batched_node_writes_label_partitioning(self, storage):
        """T015: File, Class, ExternalModule nodes land in distinct UNWIND calls."""
        mock_tx = MagicMock()

        nodes = [
            _make_ast_node("file-1", "File"),
            _make_ast_node("cls-1", "Class"),
            _make_ast_node("ext-1", "ExternalModule"),
        ]

        storage._store_node_batch(mock_tx, "proj", nodes, batch_size=500)

        assert mock_tx.run.call_count == 3
        # Verify each UNWIND query carries the correct nodes list
        calls = mock_tx.run.call_args_list
        passed_ids = set()
        for call_args in calls:
            params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
            if isinstance(params, dict) and "nodes" in params:
                for node_param in params["nodes"]:
                    passed_ids.add(node_param["id"])
        assert passed_ids == {"file-1", "cls-1", "ext-1"}

    def test_batched_node_writes_sub_batching(self, storage):
        """T015: batch_size=100 splits 300 same-label nodes into 3 UNWIND calls."""
        mock_tx = MagicMock()

        nodes = [_make_ast_node(f"c-{i}", "Class") for i in range(300)]

        count = storage._store_node_batch(mock_tx, "proj", nodes, batch_size=100)

        assert count == 300
        assert mock_tx.run.call_count == 3  # 3 sub-batches of 100


class TestUnwindRelationshipBatching:
    """T016 – UNWIND batched relationship writes grouped by type."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_batched_relationship_writes_with_unwind(self, storage):
        """T016: 2,000 relationships across 4 types → exactly 4 UNWIND tx.run calls."""
        mock_tx = MagicMock()

        # 500 pairs with repetitions; all reference the same 100 unique nodes
        all_node_ids = {f"n-{i}" for i in range(100)}
        node_pairs = [(f"n-{i % 100}", f"n-{(i + 1) % 100}") for i in range(500)]

        rels = (
            [_make_relationship(s, t, "CONTAINS") for s, t in node_pairs]
            + [_make_relationship(s, t, "CALLS") for s, t in node_pairs]
            + [_make_relationship(s, t, "REFERENCES") for s, t in node_pairs]
            + [_make_relationship(s, t, "INHERITS") for s, t in node_pairs]
        )

        stored, orphans = storage._store_relationships(
            mock_tx, "proj", rels, stored_node_ids=all_node_ids, batch_size=500
        )

        assert stored == 2000
        assert orphans == 0
        # 4 type groups, each 500 = one UNWIND call per group
        assert mock_tx.run.call_count == 4

    def test_batched_relationship_type_partitioning(self, storage):
        """T016: CONTAINS and CALLS relationships land in distinct UNWIND calls."""
        mock_tx = MagicMock()

        rels = [
            _make_relationship("n1", "n2", "CONTAINS"),
            _make_relationship("n2", "n3", "CALLS"),
        ]

        stored, orphans = storage._store_relationships(
            mock_tx, "proj", rels, stored_node_ids={"n1", "n2", "n3"}, batch_size=500
        )

        assert stored == 2
        assert orphans == 0
        assert mock_tx.run.call_count == 2  # one per type


class TestLargeAnalysisStorage:
    """T017 – Integration path: store_analysis_result with large element count."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_large_analysis_storage_performance(self, storage, neo4j_manager_mock):
        """T017: 10k elements stored without errors; call count far below 10k (UNWIND)."""
        mock_tx = MagicMock()
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        nodes = [_make_ast_node(f"n-{i}", "Class") for i in range(5000)]
        rels = [
            _make_relationship(f"n-{i}", f"n-{(i+1) % 5000}", "CONTAINS")
            for i in range(5000)
        ]
        ast_result = ASTResult(
            file_info=FileInfo(path="/large.py", name="large.py"),
            nodes=nodes,
            relationships=rels,
        )

        result = storage.store_ast_result("proj", ast_result, batch_size=500)

        assert result.nodes_stored == 5000
        assert result.relationships_stored == 5000
        # With UNWIND batching, call count should be O(groups * sub-batches), not 10k
        assert mock_tx.run.call_count < 100


class TestGraphSemanticsParity:
    """T023-T025 – Batched writes produce identical graph content as previous behavior."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_batched_writes_produce_identical_node_count(
        self, storage, neo4j_manager_mock
    ):
        """T023: nodes_stored matches input count (parity with pre-batching behavior)."""
        mock_tx = MagicMock()
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        nodes = [_make_ast_node(f"n-{i}", "Class") for i in range(1000)]
        rels = [
            _make_relationship(f"n-{i}", f"n-{(i+1) % 1000}", "CONTAINS")
            for i in range(1000)
        ]
        ast_result = ASTResult(
            file_info=FileInfo(path="/t.py", name="t.py"),
            nodes=nodes,
            relationships=rels,
        )

        result = storage.store_ast_result("proj", ast_result, batch_size=500)

        assert result.nodes_stored == 1000
        assert result.relationships_stored == 1000

    def test_batched_writes_node_properties_all_passed(self, storage):
        """T026: All node fields appear in the UNWIND parameters."""
        mock_tx = MagicMock()

        node = ASTNode(
            id="n1",
            type="Class",
            name="MyClass",
            source_file="/a.py",
            start_line=5,
            end_line=20,
            start_column=0,
            end_column=10,
            signature="class MyClass:",
            decorators=["@dataclass"],
            base_classes=["Base"],
            data_type="class",
            module_path="pkg.mod",
        )
        storage._store_node_batch(mock_tx, "proj-1", [node], batch_size=500)

        call_args = mock_tx.run.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        node_param = params["nodes"][0]

        assert node_param["id"] == "n1"
        assert node_param["project_id"] == "proj-1"
        assert node_param["type"] == "Class"
        assert node_param["name"] == "MyClass"
        assert node_param["source_file"] == "/a.py"
        assert node_param["start_line"] == 5
        assert node_param["decorators"] == ["@dataclass"]
        assert node_param["base_classes"] == ["Base"]

    def test_batched_writes_relationship_properties_all_passed(self, storage):
        """T027: All relationship fields appear in the UNWIND parameters."""
        mock_tx = MagicMock()

        rel = Relationship(source_id="s1", target_id="t1", type="CALLS")
        storage._store_relationships(
            mock_tx, "proj-1", [rel], stored_node_ids={"s1", "t1"}, batch_size=500
        )

        call_args = mock_tx.run.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        rel_param = params["rels"][0]

        assert rel_param["source_id"] == "s1"
        assert rel_param["target_id"] == "t1"
        assert rel_param["type"] == "CALLS"
        assert rel_param["project_id"] == "proj-1"

    def test_project_isolation_nodes(self, storage):
        """T028: project_id is included in every node parameter."""
        mock_tx = MagicMock()

        nodes = [_make_ast_node("n1", "File"), _make_ast_node("n2", "Class")]
        storage._store_node_batch(mock_tx, "isolated-project", nodes, batch_size=500)

        for call in mock_tx.run.call_args_list:
            params = call[0][1] if len(call[0]) > 1 else call[1]
            for np in params["nodes"]:
                assert np["project_id"] == "isolated-project"

    def test_project_isolation_relationships(self, storage):
        """T028: project_id is included in every relationship parameter."""
        mock_tx = MagicMock()

        rels = [_make_relationship("n1", "n2", "CONTAINS")]
        storage._store_relationships(
            mock_tx,
            "isolated-project",
            rels,
            stored_node_ids={"n1", "n2"},
            batch_size=500,
        )

        call_args = mock_tx.run.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert params["rels"][0]["project_id"] == "isolated-project"


class TestAtomicRollbackAndErrors:
    """T030-T035 – Error handling: rollback, orphan skip, retry, result summary."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_atomic_rollback_on_batch_write_failure(self, storage, neo4j_manager_mock):
        """T030: Non-transient batch failure raises GraphStorageError (triggers rollback)."""
        mock_tx = MagicMock()
        mock_tx.run.side_effect = Exception("constraint violation")
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        ast_result = ASTResult(
            file_info=FileInfo(path="/t.py", name="t.py"),
            nodes=[_make_ast_node("n1")],
            relationships=[],
        )

        with pytest.raises(GraphStorageError):
            storage.store_ast_result("proj", ast_result)

    def test_orphan_relationships_skipped_with_warnings(self, storage):
        """T031: Orphan relationships are skipped; valid ones are written."""
        mock_tx = MagicMock()

        # 80 valid, 20 orphan
        valid_ids = {f"v-{i}" for i in range(80)}
        valid_rels = [
            _make_relationship(f"v-{i}", f"v-{(i+1) % 80}", "CONTAINS")
            for i in range(80)
        ]
        orphan_rels = [
            _make_relationship(f"orphan-{i}", "v-0", "CONTAINS") for i in range(20)
        ]

        stored, orphans = storage._store_relationships(
            mock_tx, "proj", valid_rels + orphan_rels, stored_node_ids=valid_ids
        )

        assert stored == 80
        assert orphans == 20

    def test_store_ast_result_orphan_produces_partial_warning_status(
        self, storage, neo4j_manager_mock
    ):
        """T031: Orphan relationships set result summary status = partial_with_warnings."""
        mock_tx = MagicMock()
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        nodes = [_make_ast_node("n1")]
        rels = [_make_relationship("n1", "missing-node", "CONTAINS")]
        ast_result = ASTResult(
            file_info=FileInfo(path="/t.py", name="t.py"),
            nodes=nodes,
            relationships=rels,
        )

        result = storage.store_ast_result("proj", ast_result)

        summary = result.summary  # type: ignore[attr-defined]
        assert summary.status == "partial_with_warnings"
        assert summary.relationships_skipped_orphan == 1

    def test_retry_transient_failures_with_exponential_backoff(self, storage):
        """T032: Transient failures are retried; backoff grows exponentially."""
        from neo4j.exceptions import ServiceUnavailable

        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ServiceUnavailable("timeout")
            return "ok"

        with patch("time.sleep") as mock_sleep:
            result = storage._execute_with_retry(flaky, batch_id="test-batch")

        assert result == "ok"
        assert call_count == 3
        # backoff_ms: attempt 1 → 100ms, attempt 2 → 200ms
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert sleep_calls[0] == pytest.approx(0.1)  # 100ms
        assert sleep_calls[1] == pytest.approx(0.2)  # 200ms

    def test_retry_exhaustion_applies_failure_policy(self, storage):
        """T033: After 3 retries (4 total attempts) raises GraphStorageError."""
        from neo4j.exceptions import ServiceUnavailable

        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ServiceUnavailable("down")

        with patch("time.sleep"):
            with pytest.raises(GraphStorageError) as exc_info:
                storage._execute_with_retry(always_fails, batch_id="fail-batch")

        # 1 initial + 3 retries = 4 total attempts
        assert call_count == 4
        assert exc_info.value.error_code == "RETRY_EXHAUSTED"
        assert exc_info.value.failure_policy_applied is True

    def test_storage_result_summary_fields_always_populated(
        self, storage, neo4j_manager_mock
    ):
        """T034: StorageResultSummary always contains all required fields."""
        mock_tx = MagicMock()
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        nodes = [_make_ast_node(f"n-{i}") for i in range(10)]
        rels = [
            _make_relationship(f"n-{i}", f"n-{(i+1) % 10}", "CONTAINS")
            for i in range(10)
        ]
        ast_result = ASTResult(
            file_info=FileInfo(path="/t.py", name="t.py"),
            nodes=nodes,
            relationships=rels,
        )

        result = storage.store_ast_result("proj", ast_result)
        summary = result.summary  # type: ignore[attr-defined]

        assert hasattr(summary, "status")
        assert hasattr(summary, "nodes_processed")
        assert hasattr(summary, "relationships_processed")
        assert hasattr(summary, "batches_total")
        assert hasattr(summary, "batches_failed")
        assert hasattr(summary, "relationships_skipped_orphan")
        assert summary.nodes_processed >= 0
        assert summary.relationships_processed >= 0
        assert summary.batches_total >= 0
        assert summary.batches_failed >= 0
        assert summary.relationships_skipped_orphan >= 0

    def test_deterministic_error_on_invalid_batch_size(self, storage):
        """T035: Invalid batch_size raises ValueError with actionable message."""
        mock_tx = MagicMock()
        nodes = [_make_ast_node("n1")]

        with pytest.raises(ValueError, match=r"batch_size=50.*\[100, 1000\]"):
            storage._store_node_batch(mock_tx, "proj", nodes, batch_size=50)

        with pytest.raises(ValueError, match=r"batch_size=2000.*\[100, 1000\]"):
            storage._store_node_batch(mock_tx, "proj", nodes, batch_size=2000)

    def test_deterministic_error_on_non_transient_failure(self, storage):
        """T035: Non-transient error is raised immediately as GraphStorageError."""

        def non_transient():
            raise ValueError("schema mismatch")

        with pytest.raises(GraphStorageError) as exc_info:
            storage._execute_with_retry(non_transient, batch_id="nb")

        assert exc_info.value.error_code == "BATCH_WRITE_ERROR"


class TestHelperUtilities:
    """T011-T014 – Helper utility methods."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_validate_batch_size_accepts_valid(self, storage):
        """T011: Valid batch sizes pass the guardrail."""
        assert storage._validate_batch_size(100) == 100
        assert storage._validate_batch_size(500) == 500
        assert storage._validate_batch_size(1000) == 1000

    def test_validate_batch_size_rejects_too_small(self, storage):
        """T011: batch_size < 100 raises ValueError."""
        with pytest.raises(ValueError):
            storage._validate_batch_size(50)

    def test_validate_batch_size_rejects_too_large(self, storage):
        """T011: batch_size > 1000 raises ValueError."""
        with pytest.raises(ValueError):
            storage._validate_batch_size(2000)

    def test_calculate_exponential_backoff(self, storage):
        """T012: Backoff doubles each attempt: 100, 200, 400."""
        assert storage._calculate_exponential_backoff(1) == 100
        assert storage._calculate_exponential_backoff(2) == 200
        assert storage._calculate_exponential_backoff(3) == 400

    def test_is_transient_error_service_unavailable(self, storage):
        """T013: ServiceUnavailable is a transient error."""
        from neo4j.exceptions import ServiceUnavailable

        assert storage._is_transient_error(ServiceUnavailable("down")) is True

    def test_is_transient_error_session_expired(self, storage):
        """T013: SessionExpired is a transient error."""
        from neo4j.exceptions import SessionExpired

        assert storage._is_transient_error(SessionExpired("expired")) is True

    def test_is_transient_error_timeout_message(self, storage):
        """T013: Generic exception with 'timeout' in message is transient."""
        assert storage._is_transient_error(Exception("connection timeout")) is True

    def test_is_transient_error_non_transient(self, storage):
        """T013: ValueError is not a transient error."""
        assert storage._is_transient_error(ValueError("schema mismatch")) is False

    def test_group_records_by_category(self, storage):
        """T014: Records are correctly partitioned by key function."""
        records = [
            {"type": "A", "val": 1},
            {"type": "B", "val": 2},
            {"type": "A", "val": 3},
        ]
        groups = storage._group_records_by_category(records, lambda r: r["type"])
        assert set(groups.keys()) == {"A", "B"}
        assert len(groups["A"]) == 2
        assert len(groups["B"]) == 1


class TestBatchingModels:
    """Tests for Pydantic batching models in codeminer.models.batching."""

    def test_node_write_record_validation(self):
        """T005: NodeWriteRecord validates required fields."""
        from codeminer.models.batching import NodeWriteRecord

        record = NodeWriteRecord(
            id="n1", project_id="p1", type="Class", name="MyClass", source_file="/f.py"
        )
        assert record.id == "n1"

    def test_node_write_record_rejects_empty_id(self):
        """T005: Empty id raises validation error."""
        from codeminer.models.batching import NodeWriteRecord
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            NodeWriteRecord(
                id="",
                project_id="p1",
                type="Class",
                name="MyClass",
                source_file="/f.py",
            )

    def test_relationship_write_record_allowlist(self):
        """T006: Disallowed relationship type raises validation error."""
        from codeminer.models.batching import RelationshipWriteRecord
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            RelationshipWriteRecord(
                source_id="s1", target_id="t1", type="UNKNOWN_TYPE", project_id="p1"
            )

    def test_write_batch_batch_size_guardrails(self):
        """T007: WriteBatch enforces batch_size [100, 1000]."""
        from codeminer.models.batching import WriteBatch
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            WriteBatch(kind="node", records=[], batch_size=50)

        with pytest.raises(pydantic.ValidationError):
            WriteBatch(kind="node", records=[], batch_size=5000)

    def test_storage_result_summary_defaults(self):
        """T009: StorageResultSummary defaults to success with zero counts."""
        from codeminer.models.batching import StorageResultSummary

        s = StorageResultSummary()
        assert s.status == "success"
        assert s.nodes_processed == 0
        assert s.relationships_processed == 0
        assert s.batches_total == 0
        assert s.batches_failed == 0
        assert s.relationships_skipped_orphan == 0


class TestConfigBatchSizeGuardrails:
    """T010/T050 – Configuration defaults and guardrails."""

    def test_default_batch_size_is_500(self):
        """T050: Default GRAPH_WRITE_BATCH_SIZE is 500."""
        from codeminer.config import settings

        assert settings.graph_write_batch_size == 500

    def test_batch_size_min_is_100(self):
        """T050: GRAPH_WRITE_BATCH_SIZE_MIN is 100."""
        from codeminer.config import settings

        assert settings.graph_write_batch_size_min == 100

    def test_batch_size_max_is_1000(self):
        """T050: GRAPH_WRITE_BATCH_SIZE_MAX is 1000."""
        from codeminer.config import settings

        assert settings.graph_write_batch_size_max == 1000

    def test_invalid_batch_size_config_rejected(self):
        """T050: batch_size outside [100,1000] is rejected at config level."""
        from codeminer.config import Settings
        import pydantic

        with pytest.raises((pydantic.ValidationError, ValueError)):
            Settings(graph_write_batch_size=50, neo4j_uri="bolt://localhost:7687")


class TestEdgeCaseCoverage:
    """Coverage for empty-input guard branches and TransientError detection."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_store_node_batch_empty_returns_zero(self, storage):
        """_store_node_batch with empty list returns 0 without calling tx.run."""
        mock_tx = MagicMock()
        count = storage._store_node_batch(mock_tx, "proj", [])
        assert count == 0
        mock_tx.run.assert_not_called()

    def test_store_relationships_empty_returns_zero(self, storage):
        """_store_relationships with empty list returns (0, 0)."""
        mock_tx = MagicMock()
        stored, orphans = storage._store_relationships(mock_tx, "proj", [])
        assert stored == 0
        assert orphans == 0
        mock_tx.run.assert_not_called()

    def test_is_transient_error_neo4j_transient_error(self, storage):
        """Neo4j TransientError is detected as transient when available."""
        try:
            from neo4j.exceptions import TransientError

            assert storage._is_transient_error(TransientError({}, "transient")) is True
        except ImportError:
            pytest.skip("TransientError not available in this neo4j version")


class TestStorageAstResultFailurePaths:
    """Additional coverage for store_ast_result failure branches."""

    @pytest.fixture
    def storage(self, neo4j_manager_mock):
        return GraphStorage(neo4j_manager_mock)

    def test_graph_storage_error_reraises_and_increments_failed(
        self, storage, neo4j_manager_mock
    ):
        """GraphStorageError raised inside transaction is re-raised (batches_failed++)."""
        mock_tx = MagicMock()
        mock_tx.run.side_effect = GraphStorageError("inner batch error")
        neo4j_manager_mock.transaction.return_value.__enter__ = Mock(
            return_value=mock_tx
        )
        neo4j_manager_mock.transaction.return_value.__exit__ = Mock(return_value=False)

        nodes = [_make_ast_node("n1")]
        ast_result = ASTResult(
            file_info=FileInfo(path="/t.py", name="t.py"),
            nodes=nodes,
            relationships=[],
        )

        with pytest.raises(GraphStorageError):
            storage.store_ast_result("proj", ast_result)
