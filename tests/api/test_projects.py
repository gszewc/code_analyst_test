"""Project endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import MagicMock

from codeminer.services.project_service import ProjectService
from tests.api.conftest import create_mock_project
import tests.api.conftest as conftest
from logging import getLogger

logger = getLogger(__name__)

class TestCreateProject:
    """Test project creation endpoint."""
    
    def test_create_project_success(self, test_client: TestClient, sample_project_data: dict, sample_project_id: str, api_mocks):
        """Test successful project creation."""
        created_project = create_mock_project(sample_project_id, sample_project_data["name"])
        
        mock_service = MagicMock()
        mock_service.create = MagicMock(return_value=created_project)
        mock_service.get_by_id = MagicMock(return_value=None)
        mock_service.list_all = MagicMock(return_value=[])
        mock_service.update = MagicMock(return_value=None)
        mock_service.delete = MagicMock(return_value=None)
        
        api_mocks['services'][ProjectService] = mock_service
        api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
        response = test_client.post("/api/v1/projects/", json=sample_project_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_project_data["name"]
    
    def test_create_project_invalid_name_empty(self, test_client: TestClient):
        """Test project creation with empty name."""
        response = test_client.post("/api/v1/projects/", json={"name": ""})
        assert response.status_code == 422
    
    def test_create_project_invalid_name_too_long(self, test_client: TestClient):
        """Test project creation with name too long."""
        long_name = "a" * 256
        response = test_client.post("/api/v1/projects/", json={"name": long_name})
        assert response.status_code == 422
    
    def test_create_project_invalid_name_special_chars(self, test_client: TestClient):
        """Test project creation with invalid special characters."""
        response = test_client.post("/api/v1/projects/", json={"name": "Test@Project!"})
        assert response.status_code == 422


class TestListProjects:
    """Test project list endpoint."""
    
    def test_list_projects_empty(self, test_client: TestClient, api_mocks):
        """Test listing projects when none exist."""
        mock_service = MagicMock()
        mock_service.list_all = MagicMock(return_value=[])
        api_mocks['services'][ProjectService] = mock_service
        api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
        response = test_client.get("/api/v1/projects/")
        
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert data["total"] == 0
    
    def test_list_projects_with_data(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test listing projects with data."""
        mock_project = create_mock_project(sample_project_id)
        
        mock_service = MagicMock()
        mock_service.list_all = MagicMock(return_value=[mock_project])
        api_mocks['services'][ProjectService] = mock_service
        api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
        response = test_client.get("/api/v1/projects/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0


class TestGetProject:
    """Test get project by ID endpoint."""
    #sample_project_id: str, 
    def test_get_project_by_id(self, test_client: TestClient, api_mocks):
        """Test getting project by ID."""
        sample_project_id= conftest.PROJECT_ID
        mock_project = create_mock_project(project_id=sample_project_id)
        
        mock_service = MagicMock()
        mock_service.get_by_id = MagicMock(return_value=mock_project)
        api_mocks['services'][ProjectService] = mock_service
        api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
        response = test_client.get(f"/api/v1/projects/{sample_project_id}")
        logger.debug(f"Getting response for mock data: {response}")
        assert response.status_code == 200
    
    # TODO: FIX TEST FOR NOT FOUND
    # def test_get_project_not_found(self, test_client: TestClient, api_mocks):
    #     """Test getting non-existent project."""
    #     mock_project = create_mock_project(sample_project_id)
    #     mock_service = MagicMock()
    #     mock_service.get_by_id = MagicMock(return_value=None)
    #     api_mocks['services'][ProjectService] = mock_service
    #     api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
    #     project_id = str(uuid4())
    #     logger.debug(f"Testing get project with ID: {project_id}")
    #     response = test_client.get(f"/api/v1/projects/{project_id}")
        
        
    #     logger.debug(f"Response status code: {response.status_code}, response body: {response.text}")
    #     assert response.status_code == 404


class TestUpdateProject:
    """Test project update endpoint."""
    
    def test_update_project(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test updating project."""
        update_data = {"name": "Updated Project"}
        mock_project = create_mock_project(sample_project_id, "Updated Project")
        
        mock_service = MagicMock()
        mock_service.update = MagicMock(return_value=mock_project)
        api_mocks['services'][ProjectService] = mock_service
        api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
        response = test_client.put(f"/api/v1/projects/{sample_project_id}", json=update_data)
        
        assert response.status_code == 200


class TestDeleteProject:
    """Test project delete endpoint."""
    
    def test_delete_project(self, test_client: TestClient, api_mocks):
        """Test deleting project."""
        mock_service = MagicMock()
        mock_service.delete = MagicMock(return_value=None)
        api_mocks['services'][ProjectService] = mock_service
        api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
        project_id = str(uuid4())
        
        response = test_client.delete(f"/api/v1/projects/{project_id}")
        
        assert response.status_code == 204
    
    def test_delete_project_with_running_analysis(self, test_client: TestClient, api_mocks):
        """Test deleting project with running analysis fails."""
        mock_service = MagicMock()
        mock_service.delete = MagicMock(side_effect=ValueError("Cannot delete project with running analysis"))
        api_mocks['services'][ProjectService] = mock_service
        api_mocks['container'].get.side_effect = lambda cls: api_mocks['services'].get(cls)
        
        project_id = str(uuid4())
        
        response = test_client.delete(f"/api/v1/projects/{project_id}")
        
        assert response.status_code == 400
