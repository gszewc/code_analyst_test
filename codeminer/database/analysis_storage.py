"""
Analysis Storage - SQLite operations for analysis job tracking.

Provides CRUD operations for analysis jobs including creation,
retrieval, update, and status management.
"""

import sqlite3
import logging
import uuid
from typing import Optional, List

from .models import Analysis, DatabaseConfig
from .sqlite_manager import SqliteConnectionManager
from ..datetime_utils import ensure_utc_datetime, utc_now

logger = logging.getLogger(__name__)


class AnalysisStorage:
    """SQLite storage for analysis job tracking.

    Provides CRUD operations for analysis jobs with status tracking
    and progress updates.

    Attributes:
        connection_manager: SQLite connection manager

    Example:
        >>> config = DatabaseConfig(sqlite_path=':memory:')
        >>> manager = SqliteConnectionManager(config)
        >>> storage = AnalysisStorage(manager)
        >>> job = storage.create_job(project_id, 'pending')
    """

    # SQL statements
    SQL_CREATE = """
        INSERT INTO analyses (id, project_id, started_at, status)
        VALUES (?, ?, ?, ?)
    """

    SQL_GET = """
        SELECT id, project_id, started_at, completed_at, files_count,
               nodes_count, relationships_count, status, error_message
        FROM analyses
        WHERE id = ?
    """

    SQL_GET_BY_PROJECT = """
        SELECT id, project_id, started_at, completed_at, files_count,
               nodes_count, relationships_count, status, error_message
        FROM analyses
        WHERE project_id = ?
        ORDER BY started_at DESC
    """

    SQL_GET_RUNNING = """
        SELECT id, project_id, started_at, completed_at, files_count,
               nodes_count, relationships_count, status, error_message
        FROM analyses
        WHERE project_id = ? AND status = 'running'
    """

    SQL_UPDATE_STATUS = """
        UPDATE analyses
        SET status = ?, completed_at = ?, error_message = ?
        WHERE id = ?
    """

    SQL_UPDATE_PROGRESS = """
        UPDATE analyses
        SET files_count = ?, nodes_count = ?, relationships_count = ?
        WHERE id = ?
    """

    def __init__(self, connection_manager: SqliteConnectionManager) -> None:
        """Initialize analysis storage.

        Args:
            connection_manager: SQLite connection manager
        """
        self.connection_manager = connection_manager

    def _row_to_analysis(self, row: sqlite3.Row) -> Analysis:
        """Convert database row to Analysis model.

        Args:
            row: Database row

        Returns:
            Analysis instance
        """
        return Analysis(
            id=row['id'],
            project_id=row['project_id'],
            started_at=ensure_utc_datetime(row['started_at']),
            completed_at=ensure_utc_datetime(row['completed_at']),
            files_count=row['files_count'],
            nodes_count=row['nodes_count'],
            relationships_count=row['relationships_count'],
            status=row['status'],
            error_message=row['error_message']
        )

    def create_job(
        self,
        project_id: str,
        status: str = 'pending'
    ) -> Analysis:
        """Create a new analysis job.

        Args:
            project_id: Project UUID
            status: Initial status (default: 'pending')

        Returns:
            Created Analysis job
        """
        job_id = str(uuid.uuid4())
        now = utc_now()

        conn = self.connection_manager.get_connection()
        conn.execute(
            self.SQL_CREATE,
            (job_id, project_id, now.isoformat(), status)
        )
        conn.commit()

        logger.info(f'Created analysis job: {job_id} for project {project_id}')

        return Analysis(
            id=job_id,
            project_id=project_id,
            started_at=now,
            status=status
        )

    def get_job(self, job_id: str) -> Optional[Analysis]:
        """Get analysis job by ID.

        Args:
            job_id: Job UUID

        Returns:
            Analysis if found, None otherwise
        """
        conn = self.connection_manager.get_connection()
        cursor = conn.execute(self.SQL_GET, (job_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_analysis(row)

    def get_jobs_by_project(self, project_id: str) -> List[Analysis]:
        """Get all analysis jobs for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of Analysis jobs
        """
        conn = self.connection_manager.get_connection()
        cursor = conn.execute(self.SQL_GET_BY_PROJECT, (project_id,))
        rows = cursor.fetchall()

        return [self._row_to_analysis(row) for row in rows]

    def get_running_jobs(self, project_id: str) -> List[Analysis]:
        """Get running analysis jobs for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of running Analysis jobs
        """
        conn = self.connection_manager.get_connection()
        cursor = conn.execute(self.SQL_GET_RUNNING, (project_id,))
        rows = cursor.fetchall()

        return [self._row_to_analysis(row) for row in rows]

    def update_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update analysis job status.

        Args:
            job_id: Job UUID
            status: New status
            error_message: Optional error message (for failed status)
        """
        now = utc_now().isoformat() if status in ('completed', 'failed') else None

        conn = self.connection_manager.get_connection()
        conn.execute(
            self.SQL_UPDATE_STATUS,
            (status, now, error_message, job_id)
        )
        conn.commit()

        logger.info(f'Updated analysis job {job_id} status to {status}')

    def update_progress(
        self,
        job_id: str,
        files_count: int,
        nodes_count: int = 0,
        relationships_count: int = 0
    ) -> None:
        """Update analysis job progress.

        Args:
            job_id: Job UUID
            files_count: Number of files processed
            nodes_count: Number of nodes stored
            relationships_count: Number of relationships stored
        """
        conn = self.connection_manager.get_connection()
        conn.execute(
            self.SQL_UPDATE_PROGRESS,
            (files_count, nodes_count, relationships_count, job_id)
        )
        conn.commit()

        logger.debug(f'Updated analysis job {job_id} progress: {files_count} files')

    def start_job(self, job_id: str) -> None:
        """Mark job as running.

        Args:
            job_id: Job UUID
        """
        self.update_status(job_id, 'running')

    def complete_job(self, job_id: str, files_count: int = 0) -> None:
        """Mark job as completed.

        Args:
            job_id: Job UUID
            files_count: Number of files processed
        """
        self.update_progress(job_id, files_count)
        self.update_status(job_id, 'completed')

    def fail_job(self, job_id: str, error_message: str) -> None:
        """Mark job as failed.

        Args:
            job_id: Job UUID
            error_message: Error message
        """
        self.update_status(job_id, 'failed', error_message)
