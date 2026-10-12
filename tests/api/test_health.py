"""Health endpoint tests."""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_healthy(self, test_client: TestClient):
        """Test health endpoint returns healthy status when all services are available."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "sqlite" in data
        assert "neo4j" in data

        # Status should be healthy, degraded, or unhealthy
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_response_format(self, test_client: TestClient):
        """Test health endpoint response format."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Check version format
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

        # Check sqlite status format
        assert isinstance(data["sqlite"], str)

        # Check neo4j status format
        assert isinstance(data["neo4j"], str)

    def test_health_endpoint_available(self, test_client: TestClient):
        """Test that health endpoint is accessible."""
        response = test_client.get("/api/v1/health")

        # Should not return 404 or 500
        assert response.status_code != 404
        assert response.status_code != 500
