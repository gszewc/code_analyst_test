"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import io

from codeminer.models.analysis import AnalysisStatus
from tests.api.conftest import create_mock_project, create_mock_analysis_job, create_mock_upload_session


class TestFullWorkflow:
    """Test complete workflow from project creation to analysis."""
    
    def test_full_workflow_e2e(self, test_client: TestClient, sample_project_id: str, sample_job_id: str, api_mocks):
        """
        Test complete E2E workflow:
        1. Create project
        2. Upload ZIP file
        3. Start analysis
        4. Get analysis status
        5. Query graph nodes
        6. Search nodes
        """
        # Setup mocks
        mock_project = create_mock_project(sample_project_id)
        mock_job = create_mock_analysis_job(sample_job_id, sample_project_id, AnalysisStatus.PENDING)
        mock_upload_session = create_mock_upload_session(sample_project_id, 3)
        
        # Configure project service
        def mock_create(name, description=""):
            return mock_project
        def mock_get_by_id(pid):
            return mock_project
        def mock_list_all():
            return [mock_project]
        
        api_mocks['project_service'].create = mock_create
        api_mocks['project_service'].get_by_id = mock_get_by_id
        api_mocks['project_service'].list_all = mock_list_all
        
        # Configure file service
        def mock_upload_zip(pid, file, max_size=20*1024*1024):
            return mock_upload_session
        def mock_list_files(pid, path=""):
            return []
        def mock_discover(pid):
            return ["file1.py", "file2.py", "file3.py"]
        
        api_mocks['file_service'].upload_zip = mock_upload_zip
        api_mocks['file_service'].list_files = mock_list_files
        api_mocks['file_service'].discover_source_files = mock_discover
        
        # Configure analysis service
        def mock_create_job(pid):
            return mock_job
        def mock_get_job(jid):
            return mock_job
        def mock_get_jobs(pid):
            return [mock_job]
        
        api_mocks['analysis_service'].create_job = mock_create_job
        api_mocks['analysis_service'].get_job = mock_get_job
        api_mocks['analysis_service'].get_jobs_by_project = mock_get_jobs
        
        # Configure graph service
        def mock_get_nodes(pid, node_type=None, limit=1000, source_file=None, language=None):
            return [
                {"id": "node1", "name": "Function1", "type": "Function"},
                {"id": "node2", "name": "Class1", "type": "Class"}
            ]
        def mock_search(pid, search_term, node_type=None, limit=1000):
            return [{"id": "node1", "name": "Function1", "type": "Function"}]
        def mock_node_count(pid):
            return 2
        def mock_rel_count(pid):
            return 1
        
        api_mocks['graph_service'].get_nodes = mock_get_nodes
        api_mocks['graph_service'].search_nodes = mock_search
        api_mocks['graph_service'].get_node_count = mock_node_count
        api_mocks['graph_service'].get_relationship_count = mock_rel_count
        
        # Step 1: Create project
        response = test_client.post(
            "/api/v1/projects/",
            json={"name": "Test Project", "description": "Test"}
        )
        assert response.status_code == 201
        
        # Step 2: Upload ZIP file
        file_content = b"PK test zip content"
        file = io.BytesIO(file_content)
        response = test_client.post(
            f"/api/v1/projects/{sample_project_id}/upload",
            files={"file": ("test.zip", file, "application/zip")}
        )
        assert response.status_code == 201
        
        # Step 3: Start analysis
        response = test_client.post(f"/api/v1/analysis/projects/{sample_project_id}/analyze")
        assert response.status_code == 201
        
        # Step 4: Get analysis status
        response = test_client.get(f"/api/v1/analysis/jobs/{sample_job_id}")
        assert response.status_code == 200
        
        # Step 5: Query graph nodes
        response = test_client.get(f"/api/v1/projects/{sample_project_id}/nodes")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        
        # Step 6: Search nodes
        response = test_client.get(f"/api/v1/projects/{sample_project_id}/search?q=Function")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data


class TestProjectWithMultipleUploads:
    """Test project with multiple ZIP uploads."""
    
    def test_multiple_uploads(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test uploading multiple ZIP files to same project."""
        mock_project = create_mock_project(sample_project_id)
        mock_upload_session = create_mock_upload_session(sample_project_id, 5)
        
        def mock_get_by_id(pid):
            return mock_project
        def mock_upload_zip(pid, file, max_size=20*1024*1024):
            return mock_upload_session
        
        api_mocks['project_service'].get_by_id = mock_get_by_id
        api_mocks['file_service'].upload_zip = mock_upload_zip
        
        # First upload
        file1 = io.BytesIO(b"PK test1")
        response1 = test_client.post(
            f"/api/v1/projects/{sample_project_id}/upload",
            files={"file": ("test1.zip", file1, "application/zip")}
        )
        assert response1.status_code == 201
        
        # Second upload
        file2 = io.BytesIO(b"PK test2")
        response2 = test_client.post(
            f"/api/v1/projects/{sample_project_id}/upload",
            files={"file": ("test2.zip", file2, "application/zip")}
        )
        assert response2.status_code == 201


class TestAnalysisErrorHandling:
    """Test analysis error handling."""
    
    def test_analysis_with_no_files(self, test_client: TestClient, sample_project_id: str, sample_job_id: str, api_mocks):
        """Test analysis when no source files found."""
        mock_project = create_mock_project(sample_project_id)
        mock_job = create_mock_analysis_job(sample_job_id, sample_project_id, AnalysisStatus.FAILED)
        mock_job.error_message = "No source files found"
        
        def mock_get_by_id(pid):
            return mock_project
        def mock_create_job(pid):
            return mock_job
        def mock_get_job(jid):
            return mock_job
        def mock_discover(pid):
            return []
        
        api_mocks['project_service'].get_by_id = mock_get_by_id
        api_mocks['analysis_service'].create_job = mock_create_job
        api_mocks['analysis_service'].get_job = mock_get_job
        api_mocks['file_service'].discover_source_files = mock_discover
        
        # Start analysis
        response = test_client.post(f"/api/v1/analysis/projects/{sample_project_id}/analyze")
        assert response.status_code == 201
        
        # Check job status (should be failed)
        response = test_client.get(f"/api/v1/analysis/jobs/{sample_job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
