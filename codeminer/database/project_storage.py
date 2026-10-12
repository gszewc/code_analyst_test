"""
Project Storage - SQLite operations for project metadata.

Provides CRUD operations for project entities including creation,
retrieval, update, and deletion with cascade to Neo4j.
"""

import sqlite3
import logging
import re
from typing import Optional, List
import uuid

from .models import Project, DatabaseConfig
from .sqlite_manager import SqliteConnectionManager
from ..datetime_utils import ensure_utc_datetime, utc_now

logger = logging.getLogger(__name__)


class ProjectValidationError(Exception):
    """Exception raised for project validation errors."""
    pass


class ProjectNotFoundError(Exception):
    """Exception raised when project is not found."""
    pass


class ProjectConflictError(Exception):
    """Exception raised when project name conflicts."""
    pass


class ProjectStorage:
    """SQLite storage for project metadata.

    Provides CRUD operations for projects with validation and
    error handling.

    Attributes:
        connection_manager: SQLite connection manager

    Example:
        >>> config = DatabaseConfig(sqlite_path=':memory:')
        >>> manager = SqliteConnectionManager(config)
        >>> storage = ProjectStorage(manager)
        >>> project = storage.create_project('my-project', 'Description')
    """

    # SQL statements
    SQL_CREATE = """
        INSERT INTO projects (id, name, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """

    SQL_GET = """
        SELECT id, name, description, created_at, updated_at
        FROM projects
        WHERE id = ?
    """

    SQL_LIST = """
        SELECT id, name, description, created_at, updated_at
        FROM projects
        ORDER BY created_at DESC
        LIMIT ?
    """

    SQL_UPDATE = """
        UPDATE projects
        SET name = COALESCE(?, name),
            description = COALESCE(?, description),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """

    SQL_DELETE = """
        DELETE FROM projects WHERE id = ?
    """

    SQL_EXISTS_BY_NAME = """
        SELECT COUNT(*) FROM projects WHERE name = ?
    """

    # Validation patterns
    NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    MAX_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 1000

    def __init__(self, connection_manager: SqliteConnectionManager) -> None:
        """Initialize project storage.

        Args:
            connection_manager: SQLite connection manager
        """
        self.connection_manager = connection_manager

    def _validate_project_name(self, name: str) -> None:
        """Validate project name.

        Args:
            name: Project name to validate

        Raises:
            ProjectValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ProjectValidationError('Project name is required')

        if len(name) > self.MAX_NAME_LENGTH:
            raise ProjectValidationError(
                f'Project name must be <= {self.MAX_NAME_LENGTH} characters'
            )

        if not self.NAME_PATTERN.match(name):
            raise ProjectValidationError(
                'Project name must contain only alphanumeric characters, '
                'hyphens, and underscores'
            )

    def _validate_description(self, description: str) -> None:
        """Validate project description.

        Args:
            description: Description to validate

        Raises:
            ProjectValidationError: If description is invalid
        """
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            raise ProjectValidationError(
                f'Description must be <= {self.MAX_DESCRIPTION_LENGTH} characters'
            )

    def _project_exists_by_name(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if project exists by name.

        Args:
            name: Project name to check
            exclude_id: Optional ID to exclude (for updates)

        Returns:
            True if project exists, False otherwise
        """
        conn = self.connection_manager.get_connection()

        if exclude_id:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM projects WHERE name = ? AND id != ?',
                (name, exclude_id)
            )
        else:
            cursor = conn.execute(self.SQL_EXISTS_BY_NAME, (name,))

        return cursor.fetchone()[0] > 0

    def _row_to_project(self, row: sqlite3.Row) -> Project:
        """Convert database row to Project model.

        Args:
            row: Database row

        Returns:
            Project instance
        """
        return Project(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            created_at=ensure_utc_datetime(row['created_at']),
            updated_at=ensure_utc_datetime(row['updated_at']),
        )

    def create_project(self, name: str, description: str = '') -> Project:
        """Create a new project.

        Args:
            name: Project name (unique, alphanumeric/hyphen/underscore only)
            description: Optional project description

        Returns:
            Created project

        Raises:
            ProjectValidationError: If name or description is invalid
            ProjectConflictError: If project name already exists
        """
        # Validate
        self._validate_project_name(name)
        self._validate_description(description)

        # Check uniqueness
        if self._project_exists_by_name(name):
            raise ProjectConflictError(f"Project with name '{name}' already exists")

        # Create project
        project_id = str(uuid.uuid4())
        now = utc_now()

        conn = self.connection_manager.get_connection()
        conn.execute(
            self.SQL_CREATE,
            (project_id, name, description, now.isoformat(), now.isoformat())
        )
        conn.commit()

        logger.info(f'Created project: {project_id} ({name})')

        return Project(
            id=project_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now
        )

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project if found, None otherwise
        """
        conn = self.connection_manager.get_connection()
        cursor = conn.execute(self.SQL_GET, (project_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_project(row)

    def get_project_or_raise(self, project_id: str) -> Project:
        """Get project by ID or raise exception.

        Args:
            project_id: Project UUID

        Returns:
            Project

        Raises:
            ProjectNotFoundError: If project not found
        """
        project = self.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(f'Project not found: {project_id}')
        return project

    def list_projects(self, limit: int = 100) -> List[Project]:
        """List all projects.

        Args:
            limit: Maximum number of projects to return

        Returns:
            List of projects ordered by creation date (descending)
        """
        conn = self.connection_manager.get_connection()
        cursor = conn.execute(self.SQL_LIST, (limit,))
        rows = cursor.fetchall()

        return [self._row_to_project(row) for row in rows]

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Project:
        """Update project.

        Args:
            project_id: Project UUID
            name: Optional new name
            description: Optional new description

        Returns:
            Updated project

        Raises:
            ProjectNotFoundError: If project not found
            ProjectValidationError: If name or description is invalid
            ProjectConflictError: If new name already exists
        """
        # Verify project exists
        existing = self.get_project_or_raise(project_id)

        # Validate updates
        if name is not None:
            self._validate_project_name(name)
            if self._project_exists_by_name(name, exclude_id=project_id):
                raise ProjectConflictError(f"Project with name '{name}' already exists")

        if description is not None:
            self._validate_description(description)

        # Update
        conn = self.connection_manager.get_connection()
        conn.execute(
            self.SQL_UPDATE,
            (
                name if name is not None else existing.name,
                description if description is not None else existing.description,
                project_id
            )
        )
        conn.commit()

        logger.info(f'Updated project: {project_id}')

        # Return updated project
        return self.get_project_or_raise(project_id)

    def delete_project(self, project_id: str) -> None:
        """Delete project.

        Args:
            project_id: Project UUID

        Raises:
            ProjectNotFoundError: If project not found
        """
        # Verify project exists
        self.get_project_or_raise(project_id)

        # Delete (cascade will handle analyses)
        conn = self.connection_manager.get_connection()
        conn.execute(self.SQL_DELETE, (project_id,))
        conn.commit()

        logger.info(f'Deleted project: {project_id}')
