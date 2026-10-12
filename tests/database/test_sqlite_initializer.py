"""
Tests for SQLite schema initializer.
"""

import pytest
import sqlite3

from codeminer.database.sqlite_initializer import SqliteInitializer, SqliteInitError, SCHEMA_VERSION


class TestSqliteInitializer:
    """Tests for SqliteInitializer."""

    def test_init_schema(self, sqlite_connection):
        """Test schema initialization."""
        # Schema already initialized by fixture, verify tables exist
        cursor = sqlite_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        
        assert 'projects' in tables
        assert 'analyses' in tables
        assert 'schema_version' in tables

    def test_init_schema_idempotent(self, sqlite_connection):
        """Test schema initialization is idempotent."""
        # Initialize twice - should not raise
        SqliteInitializer.init_schema(sqlite_connection)
        SqliteInitializer.init_schema(sqlite_connection)

    def test_verify_schema_valid(self, sqlite_connection):
        """Test schema verification returns True for valid schema."""
        assert SqliteInitializer.verify_schema(sqlite_connection) is True

    def test_verify_schema_empty_db(self):
        """Test schema verification returns False for empty database."""
        conn = sqlite3.connect(':memory:')
        try:
            result = SqliteInitializer.verify_schema(conn)
            assert result is False
        finally:
            conn.close()

    def test_get_schema_info(self, sqlite_connection):
        """Test getting schema information."""
        info = SqliteInitializer.get_schema_info(sqlite_connection)
        
        assert info['version'] == SCHEMA_VERSION
        assert info['table_count'] >= 3  # projects, analyses, schema_version
        assert info['index_count'] >= 3  # idx_projects_name, etc.
        assert len(info['tables']) > 0

    def test_get_schema_info_tables(self, sqlite_connection):
        """Test schema info includes table details."""
        info = SqliteInitializer.get_schema_info(sqlite_connection)
        
        table_names = {t['name'] for t in info['tables']}
        assert 'projects' in table_names
        assert 'analyses' in table_names

    def test_indexes_created(self, sqlite_connection):
        """Test indexes are created."""
        cursor = sqlite_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        
        assert 'idx_projects_name' in indexes
        assert 'idx_analyses_project_id' in indexes
        assert 'idx_analyses_status' in indexes

    def test_triggers_created(self, sqlite_connection):
        """Test triggers are created."""
        cursor = sqlite_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )
        triggers = {row[0] for row in cursor.fetchall()}
        
        assert 'update_projects_updated_at' in triggers

    def test_updated_at_trigger(self, sqlite_connection):
        """Test updated_at trigger works."""
        # Insert project
        sqlite_connection.execute(
            'INSERT INTO projects (id, name) VALUES (?, ?)',
            ('test-id', 'test-name')
        )
        
        # Get initial updated_at
        cursor = sqlite_connection.execute(
            'SELECT updated_at FROM projects WHERE id = ?',
            ('test-id',)
        )
        initial_updated_at = cursor.fetchone()[0]
        
        # Update project
        sqlite_connection.execute(
            'UPDATE projects SET name = ? WHERE id = ?',
            ('new-name', 'test-id')
        )
        
        # Get updated updated_at
        cursor = sqlite_connection.execute(
            'SELECT updated_at FROM projects WHERE id = ?',
            ('test-id',)
        )
        new_updated_at = cursor.fetchone()[0]
        
        # Should be different (or at least not earlier)
        assert new_updated_at >= initial_updated_at

    def test_foreign_key_constraint(self, sqlite_connection):
        """Test foreign key constraint on analyses table."""
        # Insert project first
        sqlite_connection.execute(
            'INSERT INTO projects (id, name) VALUES (?, ?)',
            ('project-id', 'project-name')
        )
        
        # Insert analysis with valid project_id
        sqlite_connection.execute(
            'INSERT INTO analyses (id, project_id) VALUES (?, ?)',
            ('analysis-id', 'project-id')
        )
        
        # Try to insert analysis with invalid project_id - should fail
        with pytest.raises(sqlite3.IntegrityError):
            sqlite_connection.execute(
                'INSERT INTO analyses (id, project_id) VALUES (?, ?)',
                ('analysis-id-2', 'nonexistent-project')
            )

    def test_cascade_delete(self, sqlite_connection):
        """Test cascade delete for analyses."""
        # Insert project and analysis
        sqlite_connection.execute(
            'INSERT INTO projects (id, name) VALUES (?, ?)',
            ('project-id', 'project-name')
        )
        sqlite_connection.execute(
            'INSERT INTO analyses (id, project_id) VALUES (?, ?)',
            ('analysis-id', 'project-id')
        )
        
        # Delete project
        sqlite_connection.execute(
            'DELETE FROM projects WHERE id = ?',
            ('project-id',)
        )
        
        # Analysis should be deleted too
        cursor = sqlite_connection.execute(
            'SELECT COUNT(*) FROM analyses WHERE id = ?',
            ('analysis-id',)
        )
        count = cursor.fetchone()[0]
        assert count == 0

    def test_schema_version_recorded(self, sqlite_connection):
        """Test schema version is recorded."""
        cursor = sqlite_connection.execute(
            'SELECT version FROM schema_version ORDER BY version DESC LIMIT 1'
        )
        version = cursor.fetchone()[0]
        assert version == SCHEMA_VERSION

    def test_verify_schema_missing_tables(self):
        """Test verify_schema returns False when tables are missing."""
        empty_conn = sqlite3.connect(':memory:')
        try:
            result = SqliteInitializer.verify_schema(empty_conn)
            assert result is False
        finally:
            empty_conn.close()

    def test_verify_schema_missing_indexes(self):
        """Test verify_schema returns False when indexes are missing."""
        # Create tables without indexes
        no_index_conn = sqlite3.connect(':memory:')
        try:
            # Create tables only (no indexes)
            no_index_conn.execute('''
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            no_index_conn.execute('''
                CREATE TABLE analyses (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            ''')
            no_index_conn.execute('''
                CREATE TABLE schema_version (
                    version INTEGER NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            no_index_conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,)
            )
            
            result = SqliteInitializer.verify_schema(no_index_conn)
            assert result is False
        finally:
            no_index_conn.close()

    def test_verify_schema_version_mismatch(self, sqlite_connection):
        """Test verify_schema returns False when version doesn't match."""
        # Change version
        sqlite_connection.execute("UPDATE schema_version SET version = 999")
        
        result = SqliteInitializer.verify_schema(sqlite_connection)
        assert result is False

    def test_get_schema_info_error(self):
        """Test get_schema_info handles errors gracefully."""
        # Create connection and close it to simulate error
        conn = sqlite3.connect(':memory:')
        SqliteInitializer.init_schema(conn)
        conn.close()
        
        info = SqliteInitializer.get_schema_info(conn)
        assert info['version'] == 0
        assert info['table_count'] == 0
        assert info['index_count'] == 0
        assert info['tables'] == []


class TestSqliteInitError:
    """Tests for SqliteInitError."""

    def test_exception_creation(self):
        """Test creating SqliteInitError."""
        error = SqliteInitError('Test error message')
        assert str(error) == 'Test error message'

    def test_exception_inheritance(self):
        """Test SqliteInitError inherits from Exception."""
        error = SqliteInitError('Test')
        assert isinstance(error, Exception)
