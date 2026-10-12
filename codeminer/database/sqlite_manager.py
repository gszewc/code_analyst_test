"""
SQLite Connection Manager.

Provides singleton SQLite connection management with WAL mode configuration,
health checks, and cleanup on shutdown.
"""

import sqlite3
import atexit
import logging
from typing import Optional
from contextlib import contextmanager

from .models import DatabaseConfig

logger = logging.getLogger(__name__)


class SqliteConnectionError(Exception):
    """Exception raised for SQLite connection errors."""
    pass


class SqliteConnectionManager:
    """Singleton SQLite connection manager.

    Manages a single SQLite connection with WAL mode for better concurrency.
    Implements automatic reconnection on failure.

    Attributes:
        config: Database configuration

    Example:
        >>> config = DatabaseConfig(sqlite_path=':memory:')
        >>> manager = SqliteConnectionManager(config)
        >>> conn = manager.get_connection()
        >>> cursor = conn.execute('SELECT 1')
    """

    _instance: Optional['SqliteConnectionManager'] = None
    _connection: Optional[sqlite3.Connection] = None
    _config: Optional[DatabaseConfig] = None

    def __new__(cls, config: Optional[DatabaseConfig] = None) -> 'SqliteConnectionManager':
        """Create or return singleton instance.

        Args:
            config: Database configuration (required for first instantiation)

        Returns:
            SqliteConnectionManager instance

        Raises:
            ValueError: If config not provided on first instantiation
        """
        if cls._instance is None:
            if config is None:
                raise ValueError('DatabaseConfig required for first instantiation')
            cls._instance = super().__new__(cls)
            cls._instance._config = config
            cls._instance._init_connection()
            cls._instance._register_cleanup()
        return cls._instance

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize connection manager.

        Args:
            config: Database configuration (ignored if instance already exists)
        """
        pass  # Initialization handled in __new__

    def _init_connection(self) -> None:
        """Initialize SQLite connection with WAL mode.

        Raises:
            SqliteConnectionError: If connection cannot be established
        """
        try:
            assert self._config is not None
            logger.info(f'Initializing SQLite connection: {self._config.sqlite_path}')

            # Create connection
            self._connection = sqlite3.connect(
                self._config.sqlite_path,
                check_same_thread=False,
                isolation_level=None  # Auto-commit
            )

            # Enable Row factory for dict-like access
            self._connection.row_factory = sqlite3.Row

            # Enable WAL mode for better concurrency
            if self._config.sqlite_path != ':memory:':
                self._connection.execute('PRAGMA journal_mode=WAL')
                logger.debug('WAL mode enabled')

            # Enable foreign keys
            self._connection.execute('PRAGMA foreign_keys=ON')
            logger.debug('Foreign keys enabled')

            # Verify connection
            self._connection.execute('SELECT 1').fetchone()
            logger.info('SQLite connection established successfully')

        except sqlite3.Error as e:
            logger.error(f'Failed to initialize SQLite: {e}')
            raise SqliteConnectionError(f'Failed to initialize SQLite: {e}')

    def _register_cleanup(self) -> None:
        """Register cleanup handler for application shutdown."""
        atexit.register(self.close)
        logger.debug('Cleanup handler registered')

    def _reconnect(self) -> None:
        """Attempt to reconnect to SQLite.

        Raises:
            SqliteConnectionError: If reconnection fails
        """
        logger.info('Attempting to reconnect to SQLite')
        self._connection = None
        self._init_connection()

    def get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection.

        Returns:
            Active SQLite connection

        Raises:
            SqliteConnectionError: If connection is not available
        """
        if self._connection is None:
            self._init_connection()
            return self._connection  # type: ignore

        # Test connection
        try:
            self._connection.execute('SELECT 1')
            return self._connection
        except sqlite3.Error as e:
            logger.warning(f'Connection test failed: {e}')
            self._reconnect()
            return self._connection  # type: ignore

    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        Yields:
            sqlite3.Connection: Active connection for transaction

        Example:
            >>> with manager.transaction() as conn:
            ...     conn.execute('INSERT INTO projects ...')
            >>> # Transaction committed automatically
        """
        conn = self.get_connection()
        # Begin explicit transaction
        conn.execute('BEGIN')
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f'Transaction failed: {e}')
            raise

    def health_check(self) -> bool:
        """Check SQLite connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if self._connection is None:
            return False

        try:
            self._connection.execute('SELECT 1')
            return True
        except sqlite3.Error:
            return False

    def close(self) -> None:
        """Close SQLite connection.

        This method is safe to call multiple times.
        """
        if self._connection is not None:
            logger.info('Closing SQLite connection')
            self._connection.close()
            self._connection = None

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing).

        Warning: This closes the current connection.
        """
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None
            cls._connection = None
            cls._config = None
