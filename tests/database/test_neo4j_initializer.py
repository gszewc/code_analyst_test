"""
Tests for Neo4j schema initializer.

Note: These tests use mocks since Neo4j may not be available in test environment.
"""

import pytest
from unittest.mock import MagicMock, Mock

from codeminer.database.neo4j_initializer import (
    Neo4jInitializer,
    Neo4jInitError,
    INDEX_STATEMENTS,
    CONSTRAINT_STATEMENTS,
    PRE_INDEX_CLEANUP,
    SCHEMA_VERSION,
)


def _make_manager_mock():
    """Create a mock Neo4jConnectionManager with session context manager."""
    manager = MagicMock()
    session = MagicMock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    manager.get_session.return_value = session
    return manager, session


class TestNeo4jInitializer:
    """Tests for Neo4jInitializer."""

    def test_init_schema(self):
        """Test schema initialization runs all statements."""
        manager, session = _make_manager_mock()
        Neo4jInitializer.init_schema(manager)

        # cleanup + constraints + indexes + schema version
        expected_calls = len(PRE_INDEX_CLEANUP) + len(CONSTRAINT_STATEMENTS) + len(INDEX_STATEMENTS) + 1
        assert session.run.call_count == expected_calls

    def test_init_schema_creates_language_index(self):
        """Test that language index is included in index statements."""
        assert any('ast_node_language' in stmt for stmt in INDEX_STATEMENTS)
        assert any('n.language' in stmt for stmt in INDEX_STATEMENTS)

    def test_init_schema_cypher_error(self):
        """Test init_schema handles Cypher syntax errors."""
        from neo4j.exceptions import CypherSyntaxError

        manager, session = _make_manager_mock()
        session.run.side_effect = CypherSyntaxError('Invalid syntax')

        with pytest.raises(Neo4jInitError, match='Invalid Cypher'):
            Neo4jInitializer.init_schema(manager)

    def test_init_schema_client_error(self):
        """Test init_schema handles client errors."""
        from neo4j.exceptions import ClientError

        manager, session = _make_manager_mock()
        session.run.side_effect = ClientError('Client error')

        with pytest.raises(Neo4jInitError, match='Client error'):
            Neo4jInitializer.init_schema(manager)

    def test_init_schema_generic_error(self):
        """Test init_schema handles generic errors."""
        manager, session = _make_manager_mock()
        session.run.side_effect = Exception('Generic error')

        with pytest.raises(Neo4jInitError, match='Failed to initialize schema'):
            Neo4jInitializer.init_schema(manager)

    def test_verify_schema_version_mismatch(self):
        """Test verify_schema returns False when version doesn't match."""
        manager, session = _make_manager_mock()
        mock_result = MagicMock()
        mock_result.single.return_value = {'exists': False}
        session.run.return_value = mock_result

        result = Neo4jInitializer.verify_schema(manager)
        assert result is False

    def test_verify_schema_missing_indexes(self):
        """Test verify_schema returns False when indexes are missing."""
        manager, session = _make_manager_mock()

        # Schema version exists
        mock_version_result = MagicMock()
        mock_version_result.single.return_value = {'exists': True}

        # Missing indexes
        mock_index_result = MagicMock()
        mock_index_result.__iter__ = Mock(return_value=iter([]))

        session.run.side_effect = [mock_version_result, mock_index_result]

        result = Neo4jInitializer.verify_schema(manager)
        assert result is False

    def test_verify_schema_includes_language_index(self):
        """Test verify_schema checks for language index."""
        manager, session = _make_manager_mock()

        # Schema version exists
        mock_version_result = MagicMock()
        mock_version_result.single.return_value = {'exists': True}

        # All indexes EXCEPT language
        mock_index_result = MagicMock()
        mock_index_result.__iter__ = Mock(return_value=iter([
            {'name': 'ast_node_project_id'},
            {'name': 'ast_node_type'},

            {'name': 'ast_node_source_file'},
            {'name': 'rel_contains_project_id'},
            {'name': 'rel_extends_project_id'},
            {'name': 'rel_implements_project_id'},
            {'name': 'rel_calls_project_id'},
            {'name': 'rel_depends_on_project_id'},
            {'name': 'rel_uses_project_id'},
            {'name': 'rel_defined_in_project_id'},
        ]))

        session.run.side_effect = [mock_version_result, mock_index_result]

        result = Neo4jInitializer.verify_schema(manager)
        assert result is False

    def test_verify_schema_missing_constraints(self):
        """Test verify_schema returns False when constraints are missing."""
        manager, session = _make_manager_mock()

        mock_version_result = MagicMock()
        mock_version_result.single.return_value = {'exists': True}

        # All indexes present (including language)
        mock_index_result = MagicMock()
        mock_index_result.__iter__ = Mock(return_value=iter([
            {'name': 'ast_node_project_id'},
            {'name': 'ast_node_type'},

            {'name': 'ast_node_source_file'},
            {'name': 'ast_node_language'},
            {'name': 'rel_contains_project_id'},
            {'name': 'rel_extends_project_id'},
            {'name': 'rel_implements_project_id'},
            {'name': 'rel_calls_project_id'},
            {'name': 'rel_depends_on_project_id'},
            {'name': 'rel_uses_project_id'},
            {'name': 'rel_defined_in_project_id'},
        ]))

        # Missing constraints
        mock_constraint_result = MagicMock()
        mock_constraint_result.__iter__ = Mock(return_value=iter([]))

        session.run.side_effect = [mock_version_result, mock_index_result, mock_constraint_result]

        result = Neo4jInitializer.verify_schema(manager)
        assert result is False

    def test_verify_schema_error(self):
        """Test verify_schema returns False on error."""
        manager, session = _make_manager_mock()
        session.run.side_effect = Exception('Error')

        result = Neo4jInitializer.verify_schema(manager)
        assert result is False

    def test_verify_schema_valid(self):
        """Test verify_schema returns True when everything is present."""
        manager, session = _make_manager_mock()

        mock_version_result = MagicMock()
        mock_version_result.single.return_value = {'exists': True}

        mock_index_result = MagicMock()
        mock_index_result.__iter__ = Mock(return_value=iter([
            {'name': 'ast_node_project_id'},
            {'name': 'ast_node_type'},

            {'name': 'ast_node_source_file'},
            {'name': 'ast_node_language'},
            {'name': 'rel_contains_project_id'},
            {'name': 'rel_extends_project_id'},
            {'name': 'rel_implements_project_id'},
            {'name': 'rel_calls_project_id'},
            {'name': 'rel_depends_on_project_id'},
            {'name': 'rel_uses_project_id'},
            {'name': 'rel_defined_in_project_id'},
        ]))

        mock_constraint_result = MagicMock()
        mock_constraint_result.__iter__ = Mock(return_value=iter([
            {'name': 'ast_node_unique_id'},
        ]))

        session.run.side_effect = [mock_version_result, mock_index_result, mock_constraint_result]

        result = Neo4jInitializer.verify_schema(manager)
        assert result is True

    def test_get_schema_info(self):
        """Test get_schema_info returns schema information."""
        manager, session = _make_manager_mock()

        mock_index_result = MagicMock()
        mock_index_result.__iter__ = Mock(return_value=iter([
            {'name': 'idx1', 'labelsOrTypes': ['Node'], 'properties': ['id']}
        ]))

        mock_constraint_result = MagicMock()
        mock_constraint_result.__iter__ = Mock(return_value=iter([
            {'name': 'const1', 'type': 'UNIQUENESS', 'labelsOrTypes': ['Node'], 'properties': ['id']}
        ]))

        mock_version_result = MagicMock()
        mock_version_result.single.return_value = {'s.version': 1}

        mock_label_result = MagicMock()
        mock_label_result.__iter__ = Mock(return_value=iter([
            {'label': 'Node', 'count': 10}
        ]))

        mock_rel_result = MagicMock()
        mock_rel_result.__iter__ = Mock(return_value=iter([
            {'relationshipType': 'CONTAINS', 'count': 5}
        ]))

        session.run.side_effect = [
            mock_index_result,
            mock_constraint_result,
            mock_version_result,
            mock_label_result,
            mock_rel_result
        ]

        result = Neo4jInitializer.get_schema_info(manager)

        assert result['version'] == 1
        assert len(result['indexes']) == 1
        assert len(result['constraints']) == 1
        assert result['node_counts'] == {'Node': 10}
        assert result['relationship_counts'] == {'CONTAINS': 5}

    def test_get_schema_info_error(self):
        """Test get_schema_info returns default on error."""
        manager, session = _make_manager_mock()
        session.run.side_effect = Exception('Error')

        result = Neo4jInitializer.get_schema_info(manager)

        assert result['version'] == 0
        assert result['indexes'] == []
        assert result['constraints'] == []
        assert result['node_counts'] == {}
        assert result['relationship_counts'] == {}

    def test_get_schema_info_no_version(self):
        """Test get_schema_info handles missing version."""
        manager, session = _make_manager_mock()

        mock_index_result = MagicMock()
        mock_index_result.__iter__ = Mock(return_value=iter([]))

        mock_constraint_result = MagicMock()
        mock_constraint_result.__iter__ = Mock(return_value=iter([]))

        mock_version_result = MagicMock()
        mock_version_result.single.return_value = None

        mock_label_result = MagicMock()
        mock_label_result.__iter__ = Mock(return_value=iter([]))

        mock_rel_result = MagicMock()
        mock_rel_result.__iter__ = Mock(return_value=iter([]))

        session.run.side_effect = [
            mock_index_result,
            mock_constraint_result,
            mock_version_result,
            mock_label_result,
            mock_rel_result
        ]

        result = Neo4jInitializer.get_schema_info(manager)
        assert result['version'] == 0

    def test_schema_version_is_2(self):
        """Test schema version was bumped for language index addition."""
        assert SCHEMA_VERSION == 2


class TestNeo4jInitError:
    """Tests for Neo4jInitError."""

    def test_exception_creation(self):
        """Test creating Neo4jInitError."""
        error = Neo4jInitError('Test error message')
        assert str(error) == 'Test error message'

    def test_exception_inheritance(self):
        """Test Neo4jInitError inherits from Exception."""
        error = Neo4jInitError('Test')
        assert isinstance(error, Exception)
