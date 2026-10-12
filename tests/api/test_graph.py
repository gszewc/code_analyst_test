"""Graph endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from codeminer.database.project_storage import ProjectNotFoundError

# ---------------------------------------------------------------------------
# Shared fixture helpers for project-relationship payloads (T002)
# ---------------------------------------------------------------------------


def make_node_ref(node_id: str = "node1", node_type: str = "File") -> dict:
    """Build a minimal NodeRef payload as returned by the API."""
    return {
        "id": node_id,
        "type": node_type,
        "name": node_id,
        "source_file": f"src/{node_id}.py",
    }


def make_relationship_payload(
    source_id: str = "file:app.py",
    target_id: str = "class:App",
    rel_type: str = "CONTAINS",
    project_id: str = "123e4567-e89b-12d3-a456-426614174000",
) -> dict:
    """Build a single relationship record as returned by the API."""
    return {
        "source_id": source_id,
        "target_id": target_id,
        "type": rel_type,
        "project_id": project_id,
        "source": make_node_ref(source_id, "File"),
        "target": make_node_ref(target_id, "Class"),
    }


class TestGetNodes:
    """Test get nodes endpoint."""

    def test_get_nodes(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting all nodes."""

        def mock_get_nodes(pid, node_type=None, limit=1000, source_file=None, language=None):
            return [
                {"id": "node1", "name": "Function1", "type": "Function"},
                {"id": "node2", "name": "Class1", "type": "Class"},
            ]

        api_mocks["graph_service"].get_nodes = mock_get_nodes

        response = test_client.get(f"/api/v1/projects/{sample_project_id}/nodes")

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "total" in data

    def test_get_nodes_by_type(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting nodes filtered by type."""

        def mock_get_nodes(pid, node_type=None, limit=1000, source_file=None, language=None):
            return [{"id": "node1", "name": "Function1", "type": "Function"}]

        api_mocks["graph_service"].get_nodes = mock_get_nodes

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes?node_type=Function"
        )

        assert response.status_code == 200

    def test_get_nodes_limit(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting nodes with limit."""

        def mock_get_nodes(pid, node_type=None, limit=1000, source_file=None, language=None):
            return []

        api_mocks["graph_service"].get_nodes = mock_get_nodes

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes?limit=100"
        )

        assert response.status_code == 200

    def test_get_nodes_limit_exceeds_max(
        self, test_client: TestClient, sample_project_id: str
    ):
        """Test getting nodes with limit exceeding maximum."""
        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes?limit=20000"
        )

        assert response.status_code == 422

    def test_get_nodes_invalid_type(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test get nodes validation errors from service."""

        def mock_get_nodes(pid, node_type=None, limit=1000, source_file=None, language=None):
            raise ValueError("Unsupported node type")

        api_mocks["graph_service"].get_nodes = mock_get_nodes

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes?node_type=Unknown"
        )

        assert response.status_code == 400

    def test_get_nodes_unexpected_error(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test get nodes unexpected failure."""

        def mock_get_nodes(pid, node_type=None, limit=1000, source_file=None, language=None):
            raise RuntimeError("boom")

        api_mocks["graph_service"].get_nodes = mock_get_nodes

        response = test_client.get(f"/api/v1/projects/{sample_project_id}/nodes")

        assert response.status_code == 500

    def test_get_nodes_by_source_file(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting nodes filtered by normalized source_file."""

        def mock_get_nodes(pid, node_type=None, limit=1000, source_file=None, language=None):
            assert source_file == "application/app.py"
            return [
                {
                    "id": "node1",
                    "name": "App",
                    "type": "Class",
                    "source_file": "application/app.py",
                }
            ]

        api_mocks["graph_service"].get_nodes = mock_get_nodes

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes?source_file=application/app.py"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["nodes"][0]["source_file"] == "application/app.py"

    def test_get_nodes_invalid_source_file(
        self, test_client: TestClient, sample_project_id: str
    ):
        """Test source_file path traversal validation."""
        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes?source_file=../outside.py"
        )

        assert response.status_code == 400


class TestGetNodeById:
    """Test get node by ID endpoint."""

    def test_get_node_by_id(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting node by ID."""
        node_id = "node1"

        def mock_get_node(pid, nid):
            return {"id": node_id, "name": "Function1", "type": "Function"}

        api_mocks["graph_service"].get_node_by_id = mock_get_node

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes/{node_id}"
        )

        assert response.status_code == 200

    def test_get_node_by_id_not_found(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting non-existent node."""
        node_id = "nonexistent"

        def mock_get_node(pid, nid):
            return None

        api_mocks["graph_service"].get_node_by_id = mock_get_node

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes/{node_id}"
        )

        assert response.status_code == 404

    def test_get_node_by_id_error(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test get node by id unexpected failure."""
        node_id = "broken"

        def mock_get_node(pid, nid):
            raise RuntimeError("boom")

        api_mocks["graph_service"].get_node_by_id = mock_get_node

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes/{node_id}"
        )

        assert response.status_code == 500


class TestGetRelationships:
    """Test get relationships endpoint."""

    def test_get_relationships(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting relationships for a node."""
        node_id = "node1"

        def mock_get_rels(pid, nid, direction="both"):
            return [
                {
                    "source_id": "node1",
                    "target_id": "node2",
                    "type": "CALLS",
                    "source": {"id": "node1"},
                    "target": {"id": "node2"},
                }
            ]

        api_mocks["graph_service"].get_relationships_for_node = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes/{node_id}/relationships"
        )

        assert response.status_code == 200

    def test_get_relationships_invalid_direction(
        self, test_client: TestClient, sample_project_id: str, node_id: str = "node1"
    ):
        """Test getting relationships with invalid direction."""
        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes/{node_id}/relationships?direction=invalid"
        )

        assert response.status_code == 400

    def test_get_relationships_error(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test relationship lookup unexpected failure."""

        def mock_get_rels(pid, nid, direction="both"):
            raise RuntimeError("boom")

        api_mocks["graph_service"].get_relationships_for_node = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/nodes/node1/relationships"
        )

        assert response.status_code == 500


class TestSearchNodes:
    """Test search nodes endpoint."""

    def test_search_nodes_by_name(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test searching nodes by name."""
        search_term = "Function"

        def mock_search(pid, search_term, node_type=None, limit=1000):
            return [{"id": "node1", "name": "Function1", "type": "Function"}]

        api_mocks["graph_service"].search_nodes = mock_search

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/search?q={search_term}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert data["query"] == search_term

    def test_search_nodes_by_type(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test searching nodes with type filter."""

        def mock_search(pid, search_term, node_type=None, limit=1000):
            return []

        api_mocks["graph_service"].search_nodes = mock_search

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/search?q=test&node_type=Function"
        )

        assert response.status_code == 200

    def test_search_nodes_empty_query(
        self, test_client: TestClient, sample_project_id: str
    ):
        """Test searching with empty query."""
        response = test_client.get(f"/api/v1/projects/{sample_project_id}/search?q=")

        assert response.status_code == 422

    def test_search_nodes_invalid_query(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test search validation errors from service."""

        def mock_search(pid, search_term, node_type=None, limit=1000):
            raise ValueError("Invalid query")

        api_mocks["graph_service"].search_nodes = mock_search

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/search?q=test"
        )

        assert response.status_code == 400

    def test_search_nodes_unexpected_error(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test search unexpected failure."""

        def mock_search(pid, search_term, node_type=None, limit=1000):
            raise RuntimeError("boom")

        api_mocks["graph_service"].search_nodes = mock_search

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/search?q=test"
        )

        assert response.status_code == 500


class TestGetProjectStats:
    """Test get project statistics endpoint."""

    def test_get_project_stats(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test getting project statistics."""

        def mock_node_count(pid):
            return 100

        def mock_rel_count(pid):
            return 50

        api_mocks["graph_service"].get_node_count = mock_node_count
        api_mocks["graph_service"].get_relationship_count = mock_rel_count

        response = test_client.get(f"/api/v1/projects/{sample_project_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "node_count" in data
        assert "relationship_count" in data
        assert data["node_count"] == 100
        assert data["relationship_count"] == 50

    def test_get_project_stats_error(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Test project stats unexpected failure."""

        def mock_node_count(pid):
            raise RuntimeError("boom")

        api_mocks["graph_service"].get_node_count = mock_node_count

        response = test_client.get(f"/api/v1/projects/{sample_project_id}/stats")

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# TestGetProjectRelationships — US1, US2, US3, US4  (T009, T014, T019, T024-T026)
# ---------------------------------------------------------------------------


class TestGetProjectRelationships:
    """Tests for GET /api/v1/projects/{project_id}/relationships."""

    # --- US1: unfiltered retrieval ---

    def test_get_project_relationships_unfiltered_success(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US1: Returns all relationships when no type filter is provided."""
        rels = [
            make_relationship_payload(project_id=sample_project_id),
            make_relationship_payload(
                "class:App", "function:init", "CONTAINS", sample_project_id
            ),
        ]

        def mock_get_rels(project_id, types=None, limit=None):
            return rels

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships"
        )

        assert response.status_code == 200
        data = response.json()
        assert "relationships" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["relationships"]) == 2

    def test_get_project_relationships_empty_result(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US1: Existing project with no graph relationships returns empty list."""

        def mock_get_rels(project_id, types=None, limit=None):
            return []

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["relationships"] == []
        assert data["total"] == 0

    # --- US2: type filtering ---

    def test_get_project_relationships_single_type_filter(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US2: Returns only relationships that match a single type filter."""
        contains_rel = make_relationship_payload(
            rel_type="CONTAINS", project_id=sample_project_id
        )

        def mock_get_rels(project_id, types=None, limit=None):
            if types and "CONTAINS" in types:
                return [contains_rel]
            return []

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships?types=CONTAINS"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["relationships"][0]["type"] == "CONTAINS"

    def test_get_project_relationships_multi_type_filter(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US2: Returns only relationships matching any of the multiple specified types."""
        rels = [
            make_relationship_payload(
                rel_type="CONTAINS", project_id=sample_project_id
            ),
            make_relationship_payload("node2", "node3", "CALLS", sample_project_id),
        ]

        def mock_get_rels(project_id, types=None, limit=None):
            if types:
                return [r for r in rels if r["type"] in types]
            return rels

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships?types=CONTAINS&types=CALLS"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        types_returned = {r["type"] for r in data["relationships"]}
        assert types_returned == {"CONTAINS", "CALLS"}

    def test_get_project_relationships_duplicate_type_values(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US2: Duplicate type values do not duplicate results."""
        calls = []

        def mock_get_rels(project_id, types=None, limit=None):
            calls.append(types)
            return [
                make_relationship_payload(
                    rel_type="CONTAINS", project_id=sample_project_id
                )
            ]

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships?types=CONTAINS&types=CONTAINS"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    # --- US3: limit ---

    def test_get_project_relationships_explicit_limit(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US3: Honors explicit limit query parameter."""
        captured = {}

        def mock_get_rels(project_id, types=None, limit=None):
            captured["limit"] = limit
            return [make_relationship_payload(project_id=sample_project_id)]

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships?limit=50"
        )

        assert response.status_code == 200
        assert captured["limit"] == 50

    def test_get_project_relationships_default_limit(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US3: No limit parameter passes None to the service (service applies default)."""
        captured = {}

        def mock_get_rels(project_id, types=None, limit=None):
            captured["limit"] = limit
            return []

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships"
        )

        assert response.status_code == 200
        assert captured.get("limit") is None

    # --- US4: error handling ---

    def test_get_project_relationships_project_not_found(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US4: Returns 404 with standardized error envelope for non-existent project."""

        def mock_get_rels(project_id, types=None, limit=None):
            raise ProjectNotFoundError(f"Project not found: {project_id}")

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships"
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
        assert "message" in data["error"]
        assert "details" in data["error"]

    def test_get_project_relationships_invalid_limit_too_high(
        self, test_client: TestClient, sample_project_id: str
    ):
        """US4: Returns 422 when limit exceeds maximum (FastAPI validation)."""
        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships?limit=999999"
        )
        assert response.status_code == 422

    def test_get_project_relationships_invalid_limit_zero(
        self, test_client: TestClient, sample_project_id: str
    ):
        """US4: Returns 422 when limit is zero (FastAPI validation)."""
        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships?limit=0"
        )
        assert response.status_code == 422

    def test_get_project_relationships_invalid_project_id_format(
        self, test_client: TestClient
    ):
        """US4 FR-009: Returns 422 for invalid project_id format (not a UUID)."""
        response = test_client.get("/api/v1/projects/not-a-uuid/relationships")
        assert response.status_code == 422

    def test_get_project_relationships_400_follows_error_envelope(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US4 FR-015: 400 error response follows standardized error envelope."""

        def mock_get_rels(project_id, types=None, limit=None):
            raise ValueError("limit must be between 1 and 10000")

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships"
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]

    def test_get_project_relationships_404_follows_error_envelope(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US4 FR-015: 404 error response follows standardized error envelope."""

        def mock_get_rels(project_id, types=None, limit=None):
            raise ProjectNotFoundError("Project not found")

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships"
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error

    def test_get_project_relationships_500_follows_error_envelope(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """US4 FR-015: 500 error response follows standardized error envelope."""

        def mock_get_rels(project_id, types=None, limit=None):
            raise RuntimeError("unexpected neo4j failure")

        api_mocks["graph_service"].get_project_relationships = mock_get_rels

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/relationships"
        )

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error
