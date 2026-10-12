"""Analysis endpoint tests."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from codeminer.services.analysis_service import AnalysisService
from codeminer.models.analysis import AnalysisStatus, AnalysisStartRequest, AnalysisDefaultsResponse
from codeminer.parsing.models import NodeType, RelationshipType
from codeminer.database.models import GraphSummary
from tests.api.conftest import create_mock_analysis_job


class TestStartAnalysis:
    """Test analysis start endpoint."""
    
    def test_start_analysis_success(self, test_client: TestClient, sample_project_id: str, sample_job_id: str, api_mocks):
        """Test successful analysis start."""
        mock_job = create_mock_analysis_job(sample_job_id, sample_project_id, AnalysisStatus.PENDING)
        
        def mock_create_job(pid):
            return mock_job
        
        api_mocks['analysis_service'].create_job = mock_create_job
        
        response = test_client.post(f"/api/v1/analysis/projects/{sample_project_id}/analyze")
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
    
    def test_start_analysis_already_running(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test starting analysis when one is already running."""
        def mock_create_job(pid):
            raise ValueError("Analysis already running")
        
        api_mocks['analysis_service'].create_job = mock_create_job
        
        response = test_client.post(f"/api/v1/analysis/projects/{sample_project_id}/analyze")
        
        assert response.status_code == 400
    
    def test_start_analysis_no_files(self, test_client: TestClient, sample_project_id: str, sample_job_id: str, api_mocks):
        """Test starting analysis with no source files."""
        mock_job = create_mock_analysis_job(sample_job_id, sample_project_id, AnalysisStatus.PENDING)

        def mock_create_job(pid):
            return mock_job

        api_mocks['analysis_service'].create_job = mock_create_job

        response = test_client.post(f"/api/v1/analysis/projects/{sample_project_id}/analyze")

        assert response.status_code == 201

    def test_start_analysis_with_options(self, test_client: TestClient, sample_project_id: str, sample_job_id: str, api_mocks):
        """Test starting analysis with delete and type filter options."""
        mock_job = create_mock_analysis_job(sample_job_id, sample_project_id, AnalysisStatus.PENDING)
        api_mocks['analysis_service'].create_job = lambda pid: mock_job

        response = test_client.post(
            f"/api/v1/analysis/projects/{sample_project_id}/analyze",
            json={
                "delete_graph_data": True,
                "enabled_node_types": ["File", "Class"],
                "enabled_relationship_types": ["CONTAINS"],
            },
        )

        assert response.status_code == 201

    def test_start_analysis_empty_enabled_node_types(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test that an empty enabled_node_types list is rejected with 422."""
        response = test_client.post(
            f"/api/v1/analysis/projects/{sample_project_id}/analyze",
            json={
                "enabled_node_types": [],
            },
        )

        assert response.status_code == 422

    def test_start_analysis_empty_enabled_relationship_types(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test that an empty enabled_relationship_types list is rejected with 422."""
        response = test_client.post(
            f"/api/v1/analysis/projects/{sample_project_id}/analyze",
            json={
                "enabled_relationship_types": [],
            },
        )

        assert response.status_code == 422


class TestGetAnalysisJob:
    """Test get analysis job endpoint."""
    
    def test_get_analysis_job_status(self, test_client: TestClient, sample_job_id: str, api_mocks):
        """Test getting job status."""
        mock_job = create_mock_analysis_job(sample_job_id, status=AnalysisStatus.RUNNING)
        
        def mock_get_job(jid):
            return mock_job
        
        api_mocks['analysis_service'].get_job = mock_get_job
        
        response = test_client.get(f"/api/v1/analysis/jobs/{sample_job_id}")
        
        assert response.status_code == 200
    
    def test_get_analysis_job_not_found(self, test_client: TestClient, api_mocks):
        """Test getting non-existent job."""
        job_id = str(uuid4())
        
        def mock_get_job(jid):
            return None
        
        api_mocks['analysis_service'].get_job = mock_get_job
        
        response = test_client.get(f"/api/v1/analysis/jobs/{job_id}")
        
        assert response.status_code == 404


class TestListAnalysisJobs:
    """Test list analysis jobs endpoint."""
    
    def test_list_analysis_jobs(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test listing jobs for a project."""
        mock_job = create_mock_analysis_job(project_id=sample_project_id, status=AnalysisStatus.COMPLETED)
        
        def mock_get_jobs(pid):
            return [mock_job]
        
        api_mocks['analysis_service'].get_jobs_by_project = mock_get_jobs
        
        response = test_client.get(f"/api/v1/analysis/projects/{sample_project_id}/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data


class TestAnalysisServiceIntegration:
    """Targeted integration-style tests for analysis service orchestration."""

    @pytest.mark.asyncio
    async def test_run_analysis_passes_project_source_root_to_orchestrator(self):
        """run_analysis should thread canonical project source root into orchestrator calls."""
        project_id = uuid4()
        job_id = uuid4()
        project_path = Path(f"/tmp/uploads/project-{project_id}/source")

        project_storage = MagicMock()
        analysis_storage = MagicMock()
        graph_storage = MagicMock()
        file_manager = MagicMock()

        service = AnalysisService(
            project_storage=project_storage,
            analysis_storage=analysis_storage,
            graph_storage=graph_storage,
            file_manager=file_manager,
            parser_registry=MagicMock(),
            file_discovery=MagicMock(),
        )

        analysis_storage.get_job.return_value = MagicMock(
            id=str(job_id),
            project_id=str(project_id),
        )
        file_manager.get_safe_path.return_value = project_path
        service.orchestrator = MagicMock()
        service.orchestrator.orchestrate_analysis_for_directory = AsyncMock(return_value=None)

        await service.run_analysis(job_id)

        service.orchestrator.orchestrate_analysis_for_directory.assert_awaited_once_with(
            project_id=project_id,
            job_id=job_id,
            project_path=project_path,
            project_source_root=str(project_path),
            cross_file_config=None,
            delete_graph_data=False,
            enabled_node_types=None,
            enabled_relationship_types=None,
            languages=None,
            folders=None,
            generate_map=True,
        )

    @pytest.mark.asyncio
    async def test_run_analysis_propagates_normalization_failure_details(self):
        """Normalization failures should be recorded through analysis fail_job with explicit details."""
        project_id = uuid4()
        job_id = uuid4()
        project_path = Path(f"/tmp/uploads/project-{project_id}/source")

        project_storage = MagicMock()
        analysis_storage = MagicMock()
        graph_storage = MagicMock()
        file_manager = MagicMock()

        service = AnalysisService(
            project_storage=project_storage,
            analysis_storage=analysis_storage,
            graph_storage=graph_storage,
            file_manager=file_manager,
            parser_registry=MagicMock(),
            file_discovery=MagicMock(),
        )

        analysis_storage.get_job.return_value = MagicMock(
            id=str(job_id),
            project_id=str(project_id),
        )
        file_manager.get_safe_path.return_value = project_path
        service.orchestrator = MagicMock()
        service.orchestrator.orchestrate_analysis_for_directory = AsyncMock(
            side_effect=RuntimeError("Source path normalization failed: outside project root")
        )

        await service.run_analysis(job_id)

        analysis_storage.fail_job.assert_called_once()
        fail_message = analysis_storage.fail_job.call_args.args[1]
        assert "Analysis failed:" in fail_message
        assert "Source path normalization failed" in fail_message


class TestAnalysisModels:
    """Test analysis request/response models."""

    def test_start_request_with_all_options(self):
        """AnalysisStartRequest should accept all new fields."""
        req = AnalysisStartRequest(
            delete_graph_data=True,
            enabled_node_types=[NodeType.FILE, NodeType.CLASS],
            enabled_relationship_types=[RelationshipType.CONTAINS],
        )
        assert req.delete_graph_data is True
        assert len(req.enabled_node_types) == 2
        assert len(req.enabled_relationship_types) == 1

    def test_start_request_defaults_to_none(self):
        """All new fields should default to None."""
        req = AnalysisStartRequest()
        assert req.delete_graph_data is None
        assert req.enabled_node_types is None
        assert req.enabled_relationship_types is None

    def test_defaults_response_model(self):
        """AnalysisDefaultsResponse should serialize correctly."""
        resp = AnalysisDefaultsResponse(
            delete_graph_data=False,
            enabled_node_types=[NodeType.FILE, NodeType.CLASS],
            enabled_relationship_types=[RelationshipType.CONTAINS, RelationshipType.CALLS],
            languages=["python"],
        )
        assert resp.delete_graph_data is False
        assert len(resp.enabled_node_types) == 2


class TestGetAnalysisDefaults:
    """Test GET /analysis/defaults endpoint."""

    def test_get_defaults_returns_config(self, test_client: TestClient):
        """Should return default analysis configuration."""
        response = test_client.get("/api/v1/analysis/defaults")
        assert response.status_code == 200
        data = response.json()
        assert "delete_graph_data" in data
        assert "enabled_node_types" in data
        assert "enabled_relationship_types" in data
        assert isinstance(data["enabled_node_types"], list)
        assert isinstance(data["enabled_relationship_types"], list)


class TestGetGraphSummary:
    """Test GET /analysis/projects/{id}/graph-summary endpoint."""

    def test_get_graph_summary(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Should return node and relationship counts."""
        mock_summary = GraphSummary(
            total_nodes=142,
            nodes_by_type={"File": 10, "Class": 50, "Function": 82},
            total_relationships=380,
            relationships_by_type={"CONTAINS": 200, "CALLS": 180},
        )
        api_mocks['graph_service'].get_graph_summary.return_value = mock_summary

        response = test_client.get(
            f"/api/v1/analysis/projects/{sample_project_id}/graph-summary"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] == 142
        assert data["total_relationships"] == 380
