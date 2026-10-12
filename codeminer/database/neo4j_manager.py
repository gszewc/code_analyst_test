"""
Neo4j Connection Manager.

Provides singleton Neo4j driver management with connection pooling,
health checks, automatic reconnection, and cleanup on shutdown.
"""

import atexit
import logging
import time
from typing import Any, Optional, Generator
from contextlib import contextmanager

import neo4j
from neo4j import Driver, Session, GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from .models import DatabaseConfig

logger = logging.getLogger(__name__)


class Neo4jConnectionError(Exception):
    """Exception raised for Neo4j connection errors."""
    pass


class Neo4jConnectionManager:
    """Singleton Neo4j connection manager.

    Manages Neo4j driver with connection pooling for concurrent access.
    Implements automatic reconnection on failure.

    Attributes:
        config: Database configuration

    Example:
        >>> config = DatabaseConfig(
        ...     neo4j_uri='bolt://localhost:7687',
        ...     neo4j_user='neo4j',
        ...     neo4j_password='password',
        ...     neo4j_pool_size=50
        ... )
        >>> manager = Neo4jConnectionManager(config)
        >>> with manager.get_session() as session:
        ...     result = session.run('MATCH (n) RETURN count(n)')
    """

    _instance: Optional['Neo4jConnectionManager'] = None
    _driver: Optional[Driver] = None
    _config: Optional[DatabaseConfig] = None

    def __new__(cls, config: Optional[DatabaseConfig] = None) -> 'Neo4jConnectionManager':
        """Create or return singleton instance.

        Args:
            config: Database configuration (required for first instantiation)

        Returns:
            Neo4jConnectionManager instance

        Raises:
            ValueError: If config not provided on first instantiation
        """
        if cls._instance is None:
            if config is None:
                raise ValueError('DatabaseConfig required for first instantiation')
            cls._instance = super().__new__(cls)
            cls._instance._config = config
            cls._instance._init_driver()
            cls._instance._register_cleanup()
        return cls._instance

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize connection manager.

        Args:
            config: Database configuration (ignored if instance already exists)
        """
        pass  # Initialization handled in __new__

    def _init_driver(self) -> None:
        """Initialize Neo4j driver with connection pool.

        Raises:
            Neo4jConnectionError: If driver cannot be initialized
        """
        try:
            assert self._config is not None
            logger.info(f'Initializing Neo4j driver: {self._config.neo4j_uri}')

            # Create driver with connection pool
            self._driver = GraphDatabase.driver(
                self._config.neo4j_uri,
                auth=(self._config.neo4j_user, self._config.neo4j_password),
                max_connection_pool_size=self._config.neo4j_pool_size,
                connection_acquisition_timeout=30.0,
                connection_timeout=30.0,
                max_connection_lifetime=3600,
            )

            # Verify connection
            self._verify_connection()
            logger.info(
                f'Neo4j driver initialized (pool size: {self._config.neo4j_pool_size})'
            )

        except AuthError as e:
            logger.error(f'Neo4j authentication failed: {e}')
            raise Neo4jConnectionError(f'Authentication failed: {e}')
        except ServiceUnavailable as e:
            logger.error(f'Neo4j service unavailable: {e}')
            raise Neo4jConnectionError(f'Service unavailable: {e}')
        except Exception as e:
            logger.error(f'Failed to initialize Neo4j driver: {e}')
            raise Neo4jConnectionError(f'Failed to initialize Neo4j: {e}')

    def _verify_connection(self) -> None:
        """Verify Neo4j connection with simple query.

        Raises:
            Neo4jConnectionError: If connection verification fails
        """
        if self._driver is None:
            raise Neo4jConnectionError('Driver not initialized')

        try:
            with self._driver.session() as session:
                session.run('RETURN 1').single()
        except Exception as e:
            raise Neo4jConnectionError(f'Connection verification failed: {e}')

    def _register_cleanup(self) -> None:
        """Register cleanup handler for application shutdown."""
        atexit.register(self.close)
        logger.debug('Cleanup handler registered')

    def _reconnect(self) -> None:
        """Attempt to reconnect to Neo4j with exponential backoff.

        Raises:
            Neo4jConnectionError: If reconnection fails after max retries
        """
        assert self._config is not None
        max_retries = self._config.neo4j_max_retry
        base_delay = 0.1  # 100ms

        logger.info(f'Attempting to reconnect to Neo4j (max retries: {max_retries})')

        for attempt in range(max_retries):
            try:
                if self._driver is not None:
                    self._driver.close()

                self._init_driver()
                logger.info('Neo4j reconnection successful')
                return

            except Neo4jConnectionError as e:
                if attempt == max_retries - 1:
                    logger.error(f'Reconnection failed after {max_retries} attempts')
                    raise

                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f'Reconnection attempt {attempt + 1}/{max_retries} failed. '
                    f'Retrying in {delay:.1f}s'
                )
                time.sleep(delay)

    def get_session(self, database: Optional[str] = None) -> Session:
        """Get Neo4j session from connection pool.

        Args:
            database: Optional database name (Neo4j 4.0+)

        Returns:
            Neo4j session

        Raises:
            Neo4jConnectionError: If session cannot be obtained
        """
        if self._driver is None:
            self._init_driver()
            return self.get_session(database)  # type: ignore

        # Test driver health
        try:
            self._driver.verify_connectivity()
        except ServiceUnavailable:
            logger.warning('Driver connectivity check failed, reconnecting')
            self._reconnect()

        try:
            return self._driver.session(database=database)  # type: ignore
        except Exception as e:
            raise Neo4jConnectionError(f'Failed to get session: {e}')

    @contextmanager
    def transaction(self, database: Optional[str] = None) -> Generator[Any, None, None]:
        """Context manager for database transactions.

        Args:
            database: Optional database name (Neo4j 4.0+)

        Yields:
            Transaction: Active Neo4j transaction. Call tx.run() inside the block.

        Example:
            >>> with manager.transaction() as tx:
            ...     tx.run('CREATE (n:Node {name: $name})', name='test')
            >>> # Transaction committed automatically on exit
        """
        session = self.get_session(database)
        tx = session.begin_transaction()
        try:
            yield tx
            tx.commit()
        except Exception as e:
            tx.rollback()
            logger.error(f'Transaction failed: {e}')
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Check Neo4j connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if self._driver is None:
            return False

        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close Neo4j driver and release all connections.

        This method is safe to call multiple times.
        """
        if self._driver is not None:
            logger.info('Closing Neo4j driver')
            self._driver.close()
            self._driver = None

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing).

        Warning: This closes the current driver and all connections.
        """
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None
            cls._driver = None
            cls._config = None
