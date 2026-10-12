"""
Tests for Neo4j connection manager.

Note: These tests use mocks since Neo4j may not be available in test environment.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch

from codeminer.database.models import DatabaseConfig
from codeminer.database.neo4j_manager import Neo4jConnectionManager, Neo4jConnectionError


class TestNeo4jConnectionManager:
    """Tests for Neo4jConnectionManager."""

    def setup_method(self):
        """Reset singleton before each test."""
        Neo4jConnectionManager.reset()

    def teardown_method(self):
        """Reset singleton after each test."""
        Neo4jConnectionManager.reset()

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_singleton_pattern(self, mock_graph, db_config):
        """Test singleton pattern returns same instance."""
        # Setup mock driver
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        mock_graph.driver.return_value = mock_driver

        manager1 = Neo4jConnectionManager(db_config)
        manager2 = Neo4jConnectionManager(db_config)
        assert manager1 is manager2

    def test_initialization_required_config(self):
        """Test that config is required for first instantiation."""
        Neo4jConnectionManager.reset()
        with pytest.raises(ValueError, match='DatabaseConfig required'):
            Neo4jConnectionManager()

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_get_session(self, mock_graph, db_config):
        """Test getting Neo4j session."""
        # Setup mock
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)
        session = manager.get_session()

        assert session is not None
        # Session called at least once (may be called multiple times during verification)
        assert mock_driver.session.call_count >= 1

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_health_check_healthy(self, mock_graph, db_config):
        """Test health check returns True for healthy connection."""
        # Setup mock
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)
        assert manager.health_check() is True

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_health_check_unhealthy(self, mock_graph, db_config):
        """Test health check returns False for unhealthy connection."""
        from neo4j.exceptions import ServiceUnavailable

        # Setup mock to fail
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable('Test')
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)
        assert manager.health_check() is False

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_close(self, mock_graph, db_config):
        """Test closing driver."""
        mock_driver = MagicMock()
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)
        manager.close()

        mock_driver.close.assert_called_once()

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_close_idempotent(self, mock_graph, db_config):
        """Test close can be called multiple times safely."""
        mock_driver = MagicMock()
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)
        manager.close()
        manager.close()  # Should not raise

        assert manager._driver is None

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_reconnect_on_failure(self, mock_graph, db_config):
        """Test automatic reconnection on failure."""
        from neo4j.exceptions import ServiceUnavailable

        # Setup mock to fail first, then succeed
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = [
            ServiceUnavailable('First fail'),
            None,  # Success on retry
        ]
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)

        # Should reconnect
        session = manager.get_session()
        assert session is not None

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_transaction_context(self, mock_graph, db_config):
        """Test transaction context manager."""
        # Setup mock
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_tx = MagicMock()

        mock_tx.__enter__ = Mock(return_value=mock_tx)
        mock_tx.__exit__ = Mock(return_value=None)
        mock_session.begin_transaction.return_value = mock_tx
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)

        with manager.transaction() as tx:
            pass  # Transaction should commit

        mock_tx.commit.assert_called_once()

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_transaction_rollback(self, mock_graph, db_config):
        """Test transaction rollback on failure."""
        # Setup mock
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_tx = MagicMock()

        mock_tx.__enter__ = Mock(return_value=mock_tx)
        mock_tx.__exit__ = Mock(return_value=None)
        mock_session.begin_transaction.return_value = mock_tx
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)

        with pytest.raises(ValueError):
            with manager.transaction() as tx:
                raise ValueError('Test error')

        mock_tx.rollback.assert_called_once()

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_transaction_yields_transaction_not_session(self, mock_graph, db_config):
        """transaction() must yield the Transaction object, not the Session."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_tx = MagicMock()

        mock_tx.__enter__ = Mock(return_value=mock_tx)
        mock_tx.__exit__ = Mock(return_value=None)
        mock_session.begin_transaction.return_value = mock_tx
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)

        with manager.transaction() as obj:
            assert obj is mock_tx, (
                f"transaction() must yield the Transaction, got {type(obj)}"
            )

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_reset_classmethod(self, mock_graph, db_config):
        """Test reset classmethod clears singleton."""
        manager = Neo4jConnectionManager(db_config)
        Neo4jConnectionManager.reset()

        # Should be able to create new instance
        new_manager = Neo4jConnectionManager(db_config)
        assert new_manager is not manager

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_health_check_without_driver(self, mock_graph, db_config):
        """Test health check returns False when driver is missing."""
        manager = Neo4jConnectionManager(db_config)
        manager._driver = None

        assert manager.health_check() is False

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_verify_connection_without_driver(self, mock_graph, db_config):
        """Test verify_connection raises when driver is missing."""
        manager = Neo4jConnectionManager(db_config)
        manager._driver = None

        with pytest.raises(Neo4jConnectionError, match='Driver not initialized'):
            manager._verify_connection()

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_get_session_reinitializes_missing_driver(self, mock_graph, db_config):
        """Test get_session reinitializes the driver when absent."""
        first_driver = MagicMock()
        second_driver = MagicMock()
        second_driver.verify_connectivity.return_value = None
        second_session = MagicMock()
        second_driver.session.return_value = second_session
        mock_graph.driver.side_effect = [first_driver, second_driver]

        manager = Neo4jConnectionManager(db_config)
        manager._driver = None

        session = manager.get_session()

        assert session is second_session

    @patch('codeminer.database.neo4j_manager.GraphDatabase')
    def test_get_session_wraps_session_creation_errors(self, mock_graph, db_config):
        """Test get_session wraps driver session creation errors."""
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        mock_driver.session.return_value.__enter__ = Mock(return_value=MagicMock())
        mock_driver.session.return_value.__exit__ = Mock(return_value=None)
        mock_graph.driver.return_value = mock_driver

        manager = Neo4jConnectionManager(db_config)
        mock_driver.session.side_effect = RuntimeError('boom')

        with pytest.raises(Neo4jConnectionError, match='Failed to get session'):
            manager.get_session()


class TestNeo4jConnectionError:
    """Tests for Neo4jConnectionError."""

    def test_exception_creation(self):
        """Test creating Neo4jConnectionError."""
        error = Neo4jConnectionError('Test error message')
        assert str(error) == 'Test error message'

    def test_exception_inheritance(self):
        """Test Neo4jConnectionError inherits from Exception."""
        error = Neo4jConnectionError('Test')
        assert isinstance(error, Exception)
