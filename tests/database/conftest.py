"""
Fixtures for database layer tests.

Provides mocked and real database connections for testing.
"""

import pytest
import sqlite3
from typing import Generator
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone

from codeminer.database.models import DatabaseConfig, Project
from codeminer.database.sqlite_manager import SqliteConnectionManager
from codeminer.database.sqlite_initializer import SqliteInitializer


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime for tests."""
    return datetime.now(timezone.utc)


@pytest.fixture
def db_config():
    """Create test database configuration."""
    return DatabaseConfig(
        sqlite_path=':memory:',
        neo4j_uri='bolt://localhost:7687',
        neo4j_user='neo4j',
        neo4j_password='password',
        neo4j_pool_size=10,
        neo4j_max_retry=2
    )


@pytest.fixture
def sqlite_connection() -> Generator[sqlite3.Connection, None, None]:
    """Create in-memory SQLite connection with schema initialized."""
    conn = sqlite3.connect(':memory:')
    SqliteInitializer.init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def sqlite_manager(db_config) -> Generator[SqliteConnectionManager, None, None]:
    """Create SQLite connection manager for testing."""
    SqliteConnectionManager.reset()
    manager = SqliteConnectionManager(db_config)
    SqliteInitializer.init_schema(manager.get_connection())
    yield manager
    SqliteConnectionManager.reset()


@pytest.fixture
def sample_project() -> Project:
    """Create sample project for testing."""
    return Project(
        id='test-project-id',
        name='test-project',
        description='Test project description',
        created_at=utc_now(),
        updated_at=utc_now()
    )


@pytest.fixture
def neo4j_driver_mock() -> MagicMock:
    """Create mocked Neo4j driver for testing."""
    driver = MagicMock()
    
    # Setup session mock
    session = MagicMock()
    tx = MagicMock()
    
    # Configure transaction context manager
    tx.__enter__ = Mock(return_value=tx)
    tx.__exit__ = Mock(return_value=None)
    session.begin_transaction.return_value = tx
    
    # Configure session context manager
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    driver.session.return_value = session
    
    return driver


@pytest.fixture
def neo4j_manager_mock(db_config) -> Generator[MagicMock, None, None]:
    """Create mocked Neo4j connection manager for testing."""
    from codeminer.database.neo4j_manager import Neo4jConnectionManager

    Neo4jConnectionManager.reset()

    manager = MagicMock()

    # Setup get_session
    session = MagicMock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    manager.get_session.return_value = session

    # Setup transaction — yields a default mock tx
    tx = MagicMock()
    manager.transaction.return_value.__enter__ = Mock(return_value=tx)
    manager.transaction.return_value.__exit__ = Mock(return_value=False)

    yield manager

    Neo4jConnectionManager.reset()
