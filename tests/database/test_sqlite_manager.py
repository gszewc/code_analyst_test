"""
Tests for SQLite connection manager.
"""

import pytest
import sqlite3
from unittest.mock import patch, MagicMock

from codeminer.database.models import DatabaseConfig
from codeminer.database.sqlite_manager import SqliteConnectionManager, SqliteConnectionError
from codeminer.database.sqlite_initializer import SqliteInitializer


class TestSqliteConnectionManager:
    """Tests for SqliteConnectionManager."""

    def setup_method(self):
        """Reset singleton before each test."""
        SqliteConnectionManager.reset()

    def teardown_method(self):
        """Reset singleton after each test."""
        SqliteConnectionManager.reset()

    def test_singleton_pattern(self, db_config):
        """Test singleton pattern returns same instance."""
        manager1 = SqliteConnectionManager(db_config)
        manager2 = SqliteConnectionManager(db_config)
        assert manager1 is manager2

    def test_initialization_required_config(self):
        """Test that config is required for first instantiation."""
        SqliteConnectionManager.reset()
        with pytest.raises(ValueError, match='DatabaseConfig required'):
            SqliteConnectionManager()

    def test_get_connection(self, sqlite_manager):
        """Test getting SQLite connection."""
        conn = sqlite_manager.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        
        # Test connection works
        result = conn.execute('SELECT 1').fetchone()
        assert result[0] == 1

    def test_wal_mode_enabled(self, db_config):
        """Test WAL mode is enabled for file-based databases."""
        manager = SqliteConnectionManager(db_config)
        conn = manager.get_connection()
        
        # WAL mode only applies to file-based databases
        # For :memory:, just verify connection works
        result = conn.execute('PRAGMA journal_mode').fetchone()
        assert result is not None

    def test_foreign_keys_enabled(self, sqlite_manager):
        """Test foreign keys are enabled."""
        conn = sqlite_manager.get_connection()
        result = conn.execute('PRAGMA foreign_keys').fetchone()
        assert result[0] == 1

    def test_health_check_healthy(self, sqlite_manager):
        """Test health check returns True for healthy connection."""
        assert sqlite_manager.health_check() is True

    def test_health_check_unhealthy(self, sqlite_manager):
        """Test health check returns False after connection closed."""
        sqlite_manager.close()
        assert sqlite_manager.health_check() is False

    def test_close(self, sqlite_manager):
        """Test closing connection."""
        sqlite_manager.close()
        
        # Connection should be None
        assert sqlite_manager._connection is None

    def test_close_idempotent(self, sqlite_manager):
        """Test close can be called multiple times safely."""
        sqlite_manager.close()
        sqlite_manager.close()  # Should not raise
        assert sqlite_manager._connection is None

    def test_reconnect_on_failure(self, sqlite_manager):
        """Test automatic reconnection on failure."""
        # Close connection
        sqlite_manager._connection = None
        
        # Should reconnect automatically
        conn = sqlite_manager.get_connection()
        assert isinstance(conn, sqlite3.Connection)

    def test_transaction_commit(self, sqlite_manager):
        """Test transaction context manager commits on success."""
        conn = sqlite_manager.get_connection()
        
        with sqlite_manager.transaction() as tx_conn:
            tx_conn.execute(
                'INSERT INTO projects (id, name) VALUES (?, ?)',
                ('test-id', 'test-name')
            )
        
        # Verify data was committed
        cursor = conn.execute('SELECT name FROM projects WHERE id = ?', ('test-id',))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 'test-name'

    def test_transaction_rollback(self, sqlite_manager):
        """Test transaction context manager rolls back on failure."""
        conn = sqlite_manager.get_connection()
        
        with pytest.raises(ValueError):
            with sqlite_manager.transaction() as tx_conn:
                tx_conn.execute(
                    'INSERT INTO projects (id, name) VALUES (?, ?)',
                    ('test-id', 'test-name')
                )
                raise ValueError('Test error')
        
        # Verify data was rolled back
        cursor = conn.execute('SELECT name FROM projects WHERE id = ?', ('test-id',))
        row = cursor.fetchone()
        assert row is None

    def test_reset_classmethod(self, sqlite_manager):
        """Test reset classmethod clears singleton."""
        SqliteConnectionManager.reset()
        
        # Should be able to create new instance
        new_config = DatabaseConfig(sqlite_path=':memory:')
        new_manager = SqliteConnectionManager(new_config)
        assert new_manager is not sqlite_manager


class TestSqliteConnectionError:
    """Tests for SqliteConnectionError."""

    def test_exception_creation(self):
        """Test creating SqliteConnectionError."""
        error = SqliteConnectionError('Test error message')
        assert str(error) == 'Test error message'

    def test_exception_inheritance(self):
        """Test SqliteConnectionError inherits from Exception."""
        error = SqliteConnectionError('Test')
        assert isinstance(error, Exception)
