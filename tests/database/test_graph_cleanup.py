"""
Tests for graph cleanup utilities.

Note: These tests use mocks since Neo4j may not be available in test environment.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch, call

from codeminer.database.graph_cleanup import (
    delete_all_graph_data,
    delete_all_graph_data_by_project,
    delete_nodes_only,
    delete_relationships_only,
    delete_nodes_by_type,
    delete_relationships_by_type,
    GraphCleanup,
)
from codeminer.database.graph_storage import GraphStorage, GraphStorageError
from codeminer.database.models import DatabaseConfig


class TestDeleteAllGraphData:
    """Tests for delete_all_graph_data utility."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_all_with_config(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test global deletion with provided config."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_all.return_value = 150
        mock_storage_class.return_value = mock_storage

        config = DatabaseConfig()

        # Call function
        result = delete_all_graph_data(config=config)

        # Assertions
        assert result == 150
        mock_manager_class.assert_called_once_with(config)
        mock_storage_class.assert_called_once_with(mock_manager)
        mock_storage.delete_all.assert_called_once_with()
        mock_manager.close.assert_called_once()

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    def test_delete_all_with_existing_manager(
        self,
        mock_storage_class
    ):
        """Test global deletion with existing manager (should not close it)."""
        mock_manager = MagicMock()
        mock_storage = MagicMock()
        mock_storage.delete_all.return_value = 75
        mock_storage_class.return_value = mock_storage

        result = delete_all_graph_data(neo4j_manager=mock_manager)

        assert result == 75
        mock_storage_class.assert_called_once_with(mock_manager)
        mock_storage.delete_all.assert_called_once_with()
        mock_manager.close.assert_not_called()

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_all_default_config(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test global deletion with default config."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_all.return_value = 50
        mock_storage_class.return_value = mock_storage

        result = delete_all_graph_data()

        assert result == 50
        mock_manager_class.assert_called_once()
        mock_manager.close.assert_called_once()


class TestDeleteAllGraphDataByProject:
    """Tests for delete_all_graph_data_by_project utility."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_all_by_project_with_config(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test project-scoped deletion with provided config."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_by_project.return_value = 150
        mock_storage_class.return_value = mock_storage

        config = DatabaseConfig()
        project_id = 'test-project-123'

        result = delete_all_graph_data_by_project(project_id, config=config)

        assert result == 150
        mock_manager_class.assert_called_once_with(config)
        mock_storage_class.assert_called_once_with(mock_manager)
        mock_storage.delete_by_project.assert_called_once_with(project_id)
        mock_manager.close.assert_called_once()

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    def test_delete_all_by_project_with_existing_manager(
        self,
        mock_storage_class
    ):
        """Test project-scoped deletion with existing manager."""
        mock_manager = MagicMock()
        mock_storage = MagicMock()
        mock_storage.delete_by_project.return_value = 75
        mock_storage_class.return_value = mock_storage

        project_id = 'test-project-456'

        result = delete_all_graph_data_by_project(project_id, neo4j_manager=mock_manager)

        assert result == 75
        mock_storage_class.assert_called_once_with(mock_manager)
        mock_storage.delete_by_project.assert_called_once_with(project_id)
        mock_manager.close.assert_not_called()


class TestDeleteNodesOnly:
    """Tests for delete_nodes_only utility."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_nodes_only(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test node deletion."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_nodes_by_project.return_value = 100
        mock_storage_class.return_value = mock_storage

        result = delete_nodes_only('project-id')

        assert result == 100
        mock_storage.delete_nodes_by_project.assert_called_once_with('project-id')


class TestDeleteRelationshipsOnly:
    """Tests for delete_relationships_only utility."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_relationships_only(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test relationship deletion."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_relationships_by_project.return_value = 50
        mock_storage_class.return_value = mock_storage

        result = delete_relationships_only('project-id')

        assert result == 50
        mock_storage.delete_relationships_by_project.assert_called_once_with(
            'project-id'
        )


class TestDeleteNodesByType:
    """Tests for delete_nodes_by_type utility."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_nodes_by_type(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test type-specific node deletion."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_nodes_by_type.return_value = 30
        mock_storage_class.return_value = mock_storage

        result = delete_nodes_by_type(
            'project-id',
            node_types=['Method', 'Function']
        )

        assert result == 30
        mock_storage.delete_nodes_by_type.assert_called_once_with(
            'project-id', ['Method', 'Function']
        )


class TestDeleteRelationshipsByType:
    """Tests for delete_relationships_by_type utility."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_relationships_by_type(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test type-specific relationship deletion."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_relationships_by_type.return_value = 20
        mock_storage_class.return_value = mock_storage

        result = delete_relationships_by_type(
            'project-id',
            relationship_types=['CALLS', 'DEPENDS_ON']
        )

        assert result == 20
        mock_storage.delete_relationships_by_type.assert_called_once_with(
            'project-id', ['CALLS', 'DEPENDS_ON']
        )


class TestGraphCleanupContextManager:
    """Tests for GraphCleanup context manager."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_context_manager_enter_exit(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test context manager initialization and cleanup."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        config = DatabaseConfig()

        with GraphCleanup(config) as cleanup:
            # Verify initialization
            assert cleanup._manager is not None
            assert cleanup._storage is not None
            mock_manager_class.assert_called_once_with(config)
            mock_storage_class.assert_called_once_with(mock_manager)

        # Verify cleanup
        mock_manager.close.assert_called_once()

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_all_method(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test global delete_all method."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_all.return_value = 200
        mock_storage_class.return_value = mock_storage

        with GraphCleanup() as cleanup:
            result = cleanup.delete_all()

            assert result == 200
            mock_storage.delete_all.assert_called_once_with()

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_all_by_project_method(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test project-scoped delete_all_by_project method."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_by_project.return_value = 200
        mock_storage_class.return_value = mock_storage

        with GraphCleanup() as cleanup:
            result = cleanup.delete_all_by_project('project-id')

            assert result == 200
            mock_storage.delete_by_project.assert_called_once_with('project-id')

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_nodes_method(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test delete_nodes method."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_nodes_by_project.return_value = 80
        mock_storage_class.return_value = mock_storage

        with GraphCleanup() as cleanup:
            result = cleanup.delete_nodes('project-id')

            assert result == 80
            mock_storage.delete_nodes_by_project.assert_called_once_with(
                'project-id'
            )

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_relationships_method(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test delete_relationships method."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_relationships_by_project.return_value = 40
        mock_storage_class.return_value = mock_storage

        with GraphCleanup() as cleanup:
            result = cleanup.delete_relationships('project-id')

            assert result == 40
            mock_storage.delete_relationships_by_project.assert_called_once_with(
                'project-id'
            )

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_nodes_by_type_method(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test delete_nodes_by_type method."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_nodes_by_type.return_value = 25
        mock_storage_class.return_value = mock_storage

        with GraphCleanup() as cleanup:
            result = cleanup.delete_nodes_by_type(
                'project-id',
                ['Method', 'Class']
            )

            assert result == 25
            mock_storage.delete_nodes_by_type.assert_called_once_with(
                'project-id', ['Method', 'Class']
            )

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_delete_relationships_by_type_method(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test delete_relationships_by_type method."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_relationships_by_type.return_value = 15
        mock_storage_class.return_value = mock_storage

        with GraphCleanup() as cleanup:
            result = cleanup.delete_relationships_by_type(
                'project-id',
                ['CALLS']
            )

            assert result == 15
            mock_storage.delete_relationships_by_type.assert_called_once_with(
                'project-id', ['CALLS']
            )

    def test_context_manager_without_storage(self):
        """Test that methods raise error if storage not initialized."""
        cleanup = GraphCleanup.__new__(GraphCleanup)
        cleanup._storage = None

        with pytest.raises(GraphStorageError, match='Storage not initialized'):
            cleanup.delete_all()

        with pytest.raises(GraphStorageError, match='Storage not initialized'):
            cleanup.delete_all_by_project('project-id')

        with pytest.raises(GraphStorageError, match='Storage not initialized'):
            cleanup.delete_nodes('project-id')

        with pytest.raises(GraphStorageError, match='Storage not initialized'):
            cleanup.delete_relationships('project-id')

        with pytest.raises(GraphStorageError, match='Storage not initialized'):
            cleanup.delete_nodes_by_type('project-id', ['Method'])

        with pytest.raises(GraphStorageError, match='Storage not initialized'):
            cleanup.delete_relationships_by_type('project-id', ['CALLS'])


class TestGraphCleanupIntegration:
    """Integration-style tests for GraphCleanup."""

    @patch('codeminer.database.graph_cleanup.GraphStorage')
    @patch('codeminer.database.graph_cleanup.Neo4jConnectionManager')
    def test_multiple_operations_single_context(
        self,
        mock_manager_class,
        mock_storage_class
    ):
        """Test multiple cleanup operations reuse same connection."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_storage = MagicMock()
        mock_storage.delete_all.return_value = 100
        mock_storage.delete_by_project.return_value = 75
        mock_storage.delete_nodes_by_project.return_value = 50
        mock_storage.delete_relationships_by_project.return_value = 50
        mock_storage_class.return_value = mock_storage

        with GraphCleanup() as cleanup:
            # Perform multiple operations
            cleanup.delete_all()
            cleanup.delete_all_by_project('project-1')
            cleanup.delete_nodes('project-2')
            cleanup.delete_relationships('project-3')

        # Verify manager was created once and closed once
        assert mock_manager_class.call_count == 1
        assert mock_manager.close.call_count == 1

        # Verify all operations were called
        assert mock_storage.delete_by_project.call_count == 1
        assert mock_storage.delete_all.call_count == 1
        assert mock_storage.delete_nodes_by_project.call_count == 1
        assert mock_storage.delete_relationships_by_project.call_count == 1
