"""Dependency injection container using service locator pattern."""

from typing import Any, Callable, Dict, Optional, Type, TypeVar
from logging import getLogger

from .database.sqlite_manager import SqliteConnectionManager
from .database.neo4j_manager import Neo4jConnectionManager
from .database.project_storage import ProjectStorage
from .database.analysis_storage import AnalysisStorage
from .database.graph_storage import GraphStorage
from .database.sqlite_initializer import SqliteInitializer
from .database.neo4j_initializer import Neo4jInitializer
from .database.models import DatabaseConfig
from .parsing.registry import ParserRegistry
from .parsing.discovery import FileDiscovery
from .parsing.python.parser import PythonParser
from .parsing.java.parser import JavaParser
from .components.file_manager import FileManager
from .components.analysis_orchestrator import AnalysisOrchestrator
from .services.project_service import ProjectService
from .services.file_service import FileService
from .services.graph_service import GraphService
from .services.analysis_service import AnalysisService
from .services.repo_map_generator import RepoMapGenerator
from .config import settings

logger = getLogger(__name__)

T = TypeVar("T")


class Container:
    """
    Dependency injection container using service locator pattern.

    Supports both singleton and transient service registration.
    Services are resolved by type.
    """

    def __init__(self):
        """Initialize the container with empty registries."""
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._initialized = False

    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """
        Register a singleton instance.

        Args:
            service_type: The type to register under
            instance: The singleton instance
        """
        self._singletons[service_type] = instance
        logger.debug(f"Registered singleton: {service_type.__name__}")

    def register_factory(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory for transient instances.

        Args:
            service_type: The type to register under
            factory: Factory function that creates instances
        """
        self._factories[service_type] = factory
        logger.debug(f"Registered factory: {service_type.__name__}")

    def get(self, service_type: Type[T]) -> T:
        """
        Resolve a service by type.

        Args:
            service_type: The type of service to resolve

        Returns:
            Service instance (singleton or new transient)

        Raises:
            ValueError: If service type is not registered
        """
        # Check singletons first
        if service_type in self._singletons:
            return self._singletons[service_type]

        # Check factories
        if service_type in self._factories:
            instance = self._factories[service_type]()
            logger.debug(f"Resolved transient: {service_type.__name__}")
            return instance

        raise ValueError(f"Service not registered: {service_type.__name__}")

    def repo_map_generator(self) -> RepoMapGenerator:
        """Resolve the RepoMapGenerator singleton, creating it on first call."""
        if RepoMapGenerator not in self._singletons:
            self.register_singleton(RepoMapGenerator, RepoMapGenerator())
        return self._singletons[RepoMapGenerator]

    def analysis_orchestrator(self) -> AnalysisOrchestrator:
        """Resolve the AnalysisOrchestrator singleton, creating it on first call.

        When no full initialization has been performed the orchestrator is
        created with only *repo_map_generator* wired; all storage/registry
        dependencies are left as ``None`` so that lightweight tests (which
        only inspect wiring) can work without a real database.
        """
        if AnalysisOrchestrator not in self._singletons:
            orchestrator = AnalysisOrchestrator(
                parser_registry=self._singletons.get(ParserRegistry),
                file_discovery=self._singletons.get(FileDiscovery),
                graph_storage=self._singletons.get(GraphStorage),
                project_storage=self._singletons.get(ProjectStorage),
                analysis_storage=self._singletons.get(AnalysisStorage),
                repo_map_generator=self.repo_map_generator(),
            )
            self.register_singleton(AnalysisOrchestrator, orchestrator)
        return self._singletons[AnalysisOrchestrator]

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._singletons or service_type in self._factories

    def clear(self) -> None:
        """Clear all registrations."""
        self._singletons.clear()
        self._factories.clear()
        self._initialized = False
        logger.info("Container cleared")


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """
    Get the global container instance.

    Returns:
        The global Container instance

    Raises:
        RuntimeError: If container has not been initialized
    """
    if _container is None:
        raise RuntimeError(
            "Container not initialized. Call initialize_container() first."
        )
    return _container


def initialize_container() -> Container:
    """
    Initialize the global container with all services.

    Creates and registers:
    - DatabaseConfig (singleton)
    - SqliteConnectionManager (singleton)
    - Neo4jConnectionManager (singleton)
    - ProjectStorage (singleton)
    - AnalysisStorage (singleton)
    - GraphStorage (singleton)
    - ParserRegistry (singleton)
    - FileDiscovery (singleton)
    - FileManager (singleton)
    - RepoMapGenerator (singleton)
    - AnalysisOrchestrator (singleton)
    - ProjectService (singleton)
    - FileService (singleton)
    - GraphService (singleton)
    - AnalysisService (singleton)

    Returns:
        The initialized Container instance
    """
    global _container

    if _container is not None and _container._initialized:
        logger.info("Container already initialized")
        return _container

    logger.info("Initializing dependency injection container")

    _container = Container()

    # Create database config
    db_config = DatabaseConfig(
        sqlite_path=settings.sqlite_path,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
    )

    # Initialize database connections
    sqlite_manager = SqliteConnectionManager(db_config)
    neo4j_manager = Neo4jConnectionManager(db_config)

    # Initialize database schemas
    SqliteInitializer.init_schema(sqlite_manager.get_connection())
    logger.info("SQLite schema initialized")

    Neo4jInitializer.init_schema(neo4j_manager)
    logger.info("Neo4j schema initialized")

    # Initialize storage layers
    project_storage = ProjectStorage(sqlite_manager)
    analysis_storage = AnalysisStorage(sqlite_manager)
    graph_storage = GraphStorage(neo4j_manager)

    # Register database components as singletons
    _container.register_singleton(DatabaseConfig, db_config)
    _container.register_singleton(SqliteConnectionManager, sqlite_manager)
    _container.register_singleton(Neo4jConnectionManager, neo4j_manager)
    _container.register_singleton(ProjectStorage, project_storage)
    _container.register_singleton(AnalysisStorage, analysis_storage)
    _container.register_singleton(GraphStorage, graph_storage)

    # Initialize core components
    parser_registry = ParserRegistry()
    parser_registry.register(PythonParser())
    parser_registry.register(JavaParser())
    file_discovery = FileDiscovery(parser_registry)
    file_manager = FileManager(settings.upload_dir)

    _container.register_singleton(ParserRegistry, parser_registry)
    _container.register_singleton(FileDiscovery, file_discovery)
    _container.register_singleton(FileManager, file_manager)

    # Initialize repo map generator
    repo_map_generator = RepoMapGenerator()
    _container.register_singleton(RepoMapGenerator, repo_map_generator)

    # Initialize orchestrator
    analysis_orchestrator = AnalysisOrchestrator(
        parser_registry=parser_registry,
        file_discovery=file_discovery,
        graph_storage=graph_storage,
        project_storage=project_storage,
        analysis_storage=analysis_storage,
        repo_map_generator=repo_map_generator,
    )
    _container.register_singleton(AnalysisOrchestrator, analysis_orchestrator)

    # Initialize services
    project_service = ProjectService(project_storage)
    file_service = FileService(file_manager, project_service)
    graph_service = GraphService(graph_storage, project_storage)
    analysis_service = AnalysisService(
        project_storage=project_storage,
        analysis_storage=analysis_storage,
        graph_storage=graph_storage,
        file_manager=file_manager,
        parser_registry=parser_registry,
        file_discovery=file_discovery,
        orchestrator=analysis_orchestrator,
    )

    # Register services as singletons
    _container.register_singleton(ProjectService, project_service)
    _container.register_singleton(FileService, file_service)
    _container.register_singleton(GraphService, graph_service)
    _container.register_singleton(AnalysisService, analysis_service)

    _container._initialized = True
    logger.info("Container initialized with all services")

    return _container


def shutdown_container() -> None:
    """
    Shutdown the container and close all connections.

    Closes:
    - SqliteConnectionManager connection
    - Neo4jConnectionManager connection
    """
    global _container

    if _container is None:
        return

    logger.info("Shutting down container")

    # Close database connections
    try:
        sqlite_manager = _container.get(SqliteConnectionManager)
        sqlite_manager.close()
        logger.debug("SQLite connection closed")
    except (ValueError, Exception) as e:
        logger.error(f"Error closing SQLite connection: {e}")

    try:
        neo4j_manager = _container.get(Neo4jConnectionManager)
        neo4j_manager.close()
        logger.debug("Neo4j connection closed")
    except (ValueError, Exception) as e:
        logger.error(f"Error closing Neo4j connection: {e}")

    _container.clear()
    _container = None
    logger.info("Container shutdown complete")
