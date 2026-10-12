"""
SQLite Schema Initializer.

Provides schema initialization and verification for SQLite database,
including table creation, index creation, and schema validation.
"""

import sqlite3
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


# Schema version for tracking migrations
SCHEMA_VERSION = 1

# SQL statements for schema initialization
SCHEMA_SQL = """
-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    files_count INTEGER DEFAULT 0,
    nodes_count INTEGER DEFAULT 0,
    relationships_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

INDEX_SQL = """
-- Index for project name lookups
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- Index for analysis project lookups
CREATE INDEX IF NOT EXISTS idx_analyses_project_id ON analyses(project_id);

-- Index for analysis status filtering
CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);
"""

TRIGGER_SQL = """
-- Auto-update updated_at timestamp for projects
CREATE TRIGGER IF NOT EXISTS update_projects_updated_at
AFTER UPDATE ON projects
FOR EACH ROW
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""


class SqliteInitError(Exception):
    """Exception raised for SQLite initialization errors."""
    pass


class SqliteInitializer:
    """SQLite schema initialization.

    Initializes and verifies SQLite schema including tables, indexes,
    and triggers. Supports schema version tracking.

    Example:
        >>> conn = sqlite3.connect(':memory:')
        >>> SqliteInitializer.init_schema(conn)
        >>> assert SqliteInitializer.verify_schema(conn)
    """

    @staticmethod
    def init_schema(connection: sqlite3.Connection) -> None:
        """Initialize SQLite schema.

        Creates tables, indexes, and triggers if they don't exist.
        Records schema version.

        Args:
            connection: SQLite connection

        Raises:
            SqliteInitError: If schema initialization fails
        """
        try:
            logger.info('Initializing SQLite schema')

            # Enable foreign keys
            connection.execute('PRAGMA foreign_keys = ON')

            # Execute schema statements
            connection.executescript(SCHEMA_SQL)
            logger.debug('Tables created')

            # Create indexes
            connection.executescript(INDEX_SQL)
            logger.debug('Indexes created')

            # Create triggers
            connection.executescript(TRIGGER_SQL)
            logger.debug('Triggers created')

            # Record schema version
            connection.execute(
                'INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime("now"))',
                (SCHEMA_VERSION,)
            )
            connection.commit()

            logger.info(f'SQLite schema initialized (version {SCHEMA_VERSION})')

        except sqlite3.Error as e:
            logger.error(f'Schema initialization failed: {e}')
            raise SqliteInitError(f'Failed to initialize schema: {e}')

    @staticmethod
    def verify_schema(connection: sqlite3.Connection) -> bool:
        """Verify SQLite schema integrity.

        Checks that all required tables and indexes exist.

        Args:
            connection: SQLite connection

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            # Check required tables
            required_tables = {'projects', 'analyses', 'schema_version'}
            existing_tables = set(
                row[0] for row in
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            )

            if not required_tables.issubset(existing_tables):
                missing = required_tables - existing_tables
                logger.warning(f'Missing tables: {missing}')
                return False

            # Check schema version
            result = connection.execute(
                'SELECT version FROM schema_version ORDER BY version DESC LIMIT 1'
            ).fetchone()

            if result is None:
                logger.warning('Schema version not found')
                return False

            current_version = result[0]
            if current_version != SCHEMA_VERSION:
                logger.warning(
                    f'Schema version mismatch: expected {SCHEMA_VERSION}, got {current_version}'
                )
                return False

            # Check required indexes
            required_indexes = {
                'idx_projects_name',
                'idx_analyses_project_id',
                'idx_analyses_status'
            }
            existing_indexes = set(
                row[0] for row in
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            )

            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                logger.warning(f'Missing indexes: {missing}')
                return False

            logger.info('SQLite schema verified successfully')
            return True

        except sqlite3.Error as e:
            logger.error(f'Schema verification failed: {e}')
            return False

    @staticmethod
    def get_schema_info(connection: sqlite3.Connection) -> dict:
        """Get schema information.

        Args:
            connection: SQLite connection

        Returns:
            Dictionary with schema information
        """
        try:
            # Get table count
            table_count = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]

            # Get index count
            index_count = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
            ).fetchone()[0]

            # Get schema version
            version_result = connection.execute(
                'SELECT version FROM schema_version ORDER BY version DESC LIMIT 1'
            ).fetchone()
            schema_version = version_result[0] if version_result else 0

            # Get table details
            tables = []
            for table in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall():
                tables.append({
                    'name': table[0],
                    'sql': table[1]
                })

            return {
                'version': schema_version,
                'table_count': table_count,
                'index_count': index_count,
                'tables': tables
            }

        except sqlite3.Error as e:
            logger.error(f'Failed to get schema info: {e}')
            return {
                'version': 0,
                'table_count': 0,
                'index_count': 0,
                'tables': []
            }

    @staticmethod
    def close(connection: sqlite3.Connection) -> None:
        """Close SQLite connection.

        Args:
            connection: SQLite connection to close
        """
        if connection:
            connection.close()
            logger.debug('SQLite connection closed')
