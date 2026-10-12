"""Test fixtures for API tests."""

import pytest
from typing import Generator
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone

from codeminer.models.project import Project as ProjectModel
from codeminer.models.analysis import AnalysisJob, AnalysisStatus, AnalysisProgress
from codeminer.components.file_manager import UploadSession

def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime for tests."""
    return datetime.now(timezone.utc)


PROJECT_ID="123e4567-e89b-12d3-a456-426614174000"
def create_mock_project(project_id=PROJECT_ID, name="TestProject", description="Test Project Description"):
    """Create a proper Project model instance for mocking."""
    return ProjectModel(
        id=project_id ,
        name=name,
        description=description,
        created_at=utc_now(),
        updated_at=utc_now(),
        is_deleted=False
    )


def create_mock_analysis_job(job_id=None, project_id=None, status=AnalysisStatus.PENDING):
    """Create a proper AnalysisJob model instance for mocking."""
    return AnalysisJob(
        id=job_id or str(uuid4()),
        project_id=project_id or str(uuid4()),
        status=status,
        progress=None,
        error_message=None,
        started_at=utc_now() if status == AnalysisStatus.RUNNING else None,
        completed_at=utc_now() if status == AnalysisStatus.COMPLETED else None,
        created_at=utc_now()
    )


def create_mock_upload_session(project_id=None, file_count=5):
    """Create a proper UploadSession for mocking."""
    session_id = str(uuid4())
    proj_id = project_id or str(uuid4())
    return UploadSession(
        session_id=session_id,
        project_id=proj_id,
        file_count=file_count,
        extracted_path=f"project-{proj_id}/source"
    )


@pytest.fixture(scope="function")
def api_mocks():
    """Create all mocked services and container."""
    from codeminer.services.project_service import ProjectService
    from codeminer.services.file_service import FileService
    from codeminer.services.graph_service import GraphService
    from codeminer.services.analysis_service import AnalysisService

    # Create service mocks
    project_service = MagicMock()
    file_service = MagicMock()
    graph_service = MagicMock()
    analysis_service = MagicMock()
    
    async def mock_run_analysis(job_id, cross_file_config=None, delete_graph_data=False, enabled_node_types=None, enabled_relationship_types=None, languages=None, folders=None, generate_map=True):
        pass
    analysis_service.run_analysis = mock_run_analysis

    # Create parser registry mock
    from codeminer.parsing.registry import ParserRegistry
    parser_registry = MagicMock(spec=ParserRegistry)
    parser_registry.get_supported_languages.return_value = ["python"]

    # Create container mock
    container = MagicMock()
    services = {
        ProjectService: project_service,
        FileService: file_service,
        GraphService: graph_service,
        AnalysisService: analysis_service,
        ParserRegistry: parser_registry,
    }
    container.get.side_effect = lambda cls: services.get(cls)
    
    return {
        'container': container,
        'project_service': project_service,
        'file_service': file_service,
        'graph_service': graph_service,
        'analysis_service': analysis_service,
        'services': services,  # Direct access to services dict
    }


@pytest.fixture(scope="function")
def test_client(api_mocks) -> Generator[TestClient, None, None]:
    """Create test client for API testing with mocked container."""
    # Patch container initialization and get_container
    with patch('codeminer.container.initialize_container', return_value=api_mocks['container']):
        with patch('codeminer.container.get_container', return_value=api_mocks['container']):
            # Import app after patching to avoid real initialization
            from codeminer.api.main import app
            with TestClient(app) as client:
                yield client


@pytest.fixture
def sample_project_data() -> dict:
    """Sample project data for testing."""
    return {
        "name": "TestProject",
        "description": "A test project"
    }


@pytest.fixture
def sample_project_id() -> str:
    """Sample project UUID."""
    return str(uuid4())


@pytest.fixture
def sample_project(sample_project_id: str) -> ProjectModel:
    """Sample project with ID."""
    return create_mock_project(sample_project_id)


@pytest.fixture
def sample_job_id() -> str:
    """Sample job UUID."""
    return str(uuid4())


@pytest.fixture
def sample_analysis_job(sample_job_id: str, sample_project_id: str) -> AnalysisJob:
    """Sample analysis job."""
    return create_mock_analysis_job(sample_job_id, sample_project_id)


@pytest.fixture
def sample_upload_session(sample_project_id: str) -> UploadSession:
    """Sample upload session."""
    return create_mock_upload_session(sample_project_id)
