"""Tests for AnalysisStorage."""

from datetime import timezone

from codeminer.database.analysis_storage import AnalysisStorage


def insert_project(sqlite_manager, sample_project) -> None:
    """Insert a project row for analysis foreign-key references."""
    conn = sqlite_manager.get_connection()
    conn.execute(
        """
        INSERT INTO projects (id, name, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            sample_project.id,
            sample_project.name,
            sample_project.description,
            sample_project.created_at.isoformat(),
            sample_project.updated_at.isoformat(),
        ),
    )
    conn.commit()


class TestAnalysisStorage:
    """Tests for SQLite-backed analysis storage."""

    def test_create_and_get_job(self, sqlite_manager, sample_project):
        """Test creating and retrieving an analysis job."""
        insert_project(sqlite_manager, sample_project)
        storage = AnalysisStorage(sqlite_manager)

        job = storage.create_job(sample_project.id, status='pending')
        loaded = storage.get_job(job.id)

        assert loaded is not None
        assert loaded.id == job.id
        assert loaded.project_id == sample_project.id
        assert loaded.status == 'pending'
        assert loaded.started_at.tzinfo == timezone.utc

    def test_get_job_missing_returns_none(self, sqlite_manager):
        """Test missing job lookup returns None."""
        storage = AnalysisStorage(sqlite_manager)

        assert storage.get_job('missing-job') is None

    def test_get_jobs_by_project_and_running_filter(self, sqlite_manager, sample_project):
        """Test listing project jobs and filtering running jobs."""
        insert_project(sqlite_manager, sample_project)
        storage = AnalysisStorage(sqlite_manager)

        pending_job = storage.create_job(sample_project.id, status='pending')
        running_job = storage.create_job(sample_project.id, status='running')

        all_jobs = storage.get_jobs_by_project(sample_project.id)
        running_jobs = storage.get_running_jobs(sample_project.id)

        assert [job.id for job in all_jobs] == [running_job.id, pending_job.id]
        assert [job.id for job in running_jobs] == [running_job.id]

    def test_update_status_and_progress(self, sqlite_manager, sample_project):
        """Test updating status, completion timestamp, and progress counters."""
        insert_project(sqlite_manager, sample_project)
        storage = AnalysisStorage(sqlite_manager)

        job = storage.create_job(sample_project.id, status='pending')
        storage.update_progress(job.id, files_count=3, nodes_count=10, relationships_count=7)
        storage.update_status(job.id, 'completed')

        loaded = storage.get_job(job.id)

        assert loaded is not None
        assert loaded.status == 'completed'
        assert loaded.files_count == 3
        assert loaded.nodes_count == 10
        assert loaded.relationships_count == 7
        assert loaded.completed_at is not None
        assert loaded.completed_at.tzinfo == timezone.utc

    def test_start_complete_and_fail_helpers(self, sqlite_manager, sample_project):
        """Test helper methods for starting, completing, and failing jobs."""
        insert_project(sqlite_manager, sample_project)
        storage = AnalysisStorage(sqlite_manager)

        running_job = storage.create_job(sample_project.id, status='pending')
        storage.start_job(running_job.id)
        running_loaded = storage.get_job(running_job.id)
        assert running_loaded is not None
        assert running_loaded.status == 'running'
        assert running_loaded.completed_at is None

        completed_job = storage.create_job(sample_project.id, status='pending')
        storage.complete_job(completed_job.id, files_count=5)
        completed_loaded = storage.get_job(completed_job.id)
        assert completed_loaded is not None
        assert completed_loaded.status == 'completed'
        assert completed_loaded.files_count == 5
        assert completed_loaded.completed_at is not None

        failed_job = storage.create_job(sample_project.id, status='pending')
        storage.fail_job(failed_job.id, 'parser error')
        failed_loaded = storage.get_job(failed_job.id)
        assert failed_loaded is not None
        assert failed_loaded.status == 'failed'
        assert failed_loaded.error_message == 'parser error'
        assert failed_loaded.completed_at is not None
