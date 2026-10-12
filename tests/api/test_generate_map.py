"""Tests for the POST /analysis/projects/{id}/generate-map endpoint."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from tests.api.conftest import create_mock_project


PROJECT_ID = "123e4567-e89b-12d3-a456-426614174001"


class TestGenerateMapEndpoint:
    def test_generate_map_success(self, test_client, api_mocks):
        """POST /generate-map returns 200 with status ok."""
        project = create_mock_project(PROJECT_ID)
        api_mocks["project_service"].get_project.return_value = project

        async def mock_generate(project_id, languages=None, folders=None):
            pass

        api_mocks["analysis_service"].generate_map_for_project = mock_generate

        response = test_client.post(
            f"/api/v1/analysis/projects/{PROJECT_ID}/generate-map"
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "path": "repomap.txt"}

    def test_generate_map_project_not_found_returns_404(self, test_client, api_mocks):
        """When project does not exist, returns 404."""
        async def mock_generate(project_id, languages=None, folders=None):
            raise ValueError(f"Project not found: {project_id}")

        api_mocks["analysis_service"].generate_map_for_project = mock_generate

        response = test_client.post(
            f"/api/v1/analysis/projects/{PROJECT_ID}/generate-map"
        )

        assert response.status_code == 404

    def test_generate_map_no_files_returns_400(self, test_client, api_mocks):
        """When project has no source files, returns 400."""
        async def mock_generate(project_id, languages=None, folders=None):
            raise FileNotFoundError(f"No source files found for project {project_id}")

        api_mocks["analysis_service"].generate_map_for_project = mock_generate

        response = test_client.post(
            f"/api/v1/analysis/projects/{PROJECT_ID}/generate-map"
        )

        assert response.status_code == 400

    def test_generate_map_unexpected_error_returns_500(self, test_client, api_mocks):
        """When an unexpected error occurs, returns 500."""
        async def mock_generate(project_id, languages=None, folders=None):
            raise Exception("boom")

        api_mocks["analysis_service"].generate_map_for_project = mock_generate

        response = test_client.post(
            f"/api/v1/analysis/projects/{PROJECT_ID}/generate-map"
        )

        assert response.status_code == 500

    def test_start_analysis_with_generate_map_false(self, test_client, api_mocks):
        """POST /analyze with generate_map=false passes flag to service."""
        from codeminer.models.analysis import AnalysisJob, AnalysisStatus

        job = AnalysisJob(
            id=str(uuid4()),
            project_id=PROJECT_ID,
            status=AnalysisStatus.PENDING,
            progress=None,
            error_message=None,
            started_at=None,
            completed_at=None,
        )
        api_mocks["analysis_service"].create_job.return_value = job

        calls = []

        async def mock_run_analysis(
            job_id, cross_file_config=None, delete_graph_data=False,
            enabled_node_types=None, enabled_relationship_types=None,
            languages=None, folders=None, generate_map=True,
        ):
            calls.append(generate_map)

        api_mocks["analysis_service"].run_analysis = mock_run_analysis

        response = test_client.post(
            f"/api/v1/analysis/projects/{PROJECT_ID}/analyze",
            json={"generate_map": False},
        )

        assert response.status_code == 201
        # Background task runs synchronously in TestClient
        assert calls == [False]

    def test_start_analysis_default_generate_map_true(self, test_client, api_mocks):
        """POST /analyze without generate_map defaults to True."""
        from codeminer.models.analysis import AnalysisJob, AnalysisStatus

        job = AnalysisJob(
            id=str(uuid4()),
            project_id=PROJECT_ID,
            status=AnalysisStatus.PENDING,
            progress=None,
            error_message=None,
            started_at=None,
            completed_at=None,
        )
        api_mocks["analysis_service"].create_job.return_value = job

        calls = []

        async def mock_run_analysis(
            job_id, cross_file_config=None, delete_graph_data=False,
            enabled_node_types=None, enabled_relationship_types=None,
            languages=None, folders=None, generate_map=True,
        ):
            calls.append(generate_map)

        api_mocks["analysis_service"].run_analysis = mock_run_analysis

        response = test_client.post(
            f"/api/v1/analysis/projects/{PROJECT_ID}/analyze",
            json={},
        )

        assert response.status_code == 201
        assert calls == [True]
