"""
Tests for Neo4j cleanup CLI.

Note: These tests use mocks since Neo4j may not be available in test environment.
"""

import pytest
import argparse
from unittest.mock import MagicMock, Mock, patch, call
from io import StringIO

from codeminer.database.cli import (
    create_cli,
    run_command,
    OutputFormatter,
    confirm_deletion,
    create_config,
    run_health_check,
    run_status,
    run_delete_all,
    run_delete_all_by_project,
    run_delete_nodes,
    run_delete_relationships,
    run_delete_nodes_by_type,
    run_delete_relationships_by_type,
)
from codeminer.database.models import DatabaseConfig
from codeminer.database.graph_storage import GraphStorageError
from codeminer.database.neo4j_manager import Neo4jConnectionError


class TestCreateCLI:
    """Tests for CLI argument parser creation."""

    def test_create_cli_basic(self):
        """Test CLI parser creation."""
        parser = create_cli()
        assert parser is not None
        assert parser.prog == 'neo4j-cleanup'

    def test_create_cli_global_options(self):
        """Test global options are defined."""
        parser = create_cli()
        args = parser.parse_args([
            '--neo4j-uri', 'bolt://test:7687',
            '--neo4j-user', 'testuser',
            '--neo4j-password', 'testpass',
            '--quiet',
            '--json',
            '--dry-run',
            'health'
        ])

        assert args.neo4j_uri == 'bolt://test:7687'
        assert args.neo4j_user == 'testuser'
        assert args.neo4j_password == 'testpass'
        assert args.quiet is True
        assert args.json is True
        assert args.dry_run is True

    def test_create_cli_subcommands(self):
        """Test subcommands are defined."""
        parser = create_cli()
        
        # Test delete-all
        args = parser.parse_args(['delete-all'])
        assert args.command == 'delete-all'

        # Test delete-all-by-project
        args = parser.parse_args(['delete-all-by-project', 'project-123'])
        assert args.command == 'delete-all-by-project'
        assert args.project_id == 'project-123'

        # Test delete-nodes
        args = parser.parse_args(['delete-nodes', 'project-123'])
        assert args.command == 'delete-nodes'

        # Test delete-relationships
        args = parser.parse_args(['delete-relationships', 'project-123'])
        assert args.command == 'delete-relationships'

        # Test delete-nodes-by-type
        args = parser.parse_args([
            'delete-nodes-by-type', 'project-123',
            '--types', 'Method', 'Function'
        ])
        assert args.command == 'delete-nodes-by-type'
        assert args.types == ['Method', 'Function']

        # Test delete-relationships-by-type
        args = parser.parse_args([
            'delete-relationships-by-type', 'project-123',
            '--types', 'CALLS', 'DEPENDS_ON'
        ])
        assert args.command == 'delete-relationships-by-type'
        assert args.types == ['CALLS', 'DEPENDS_ON']

        # Test status
        args = parser.parse_args(['status', 'project-123'])
        assert args.command == 'status'

        # Test health
        args = parser.parse_args(['health'])
        assert args.command == 'health'

    def test_create_cli_force_flag(self):
        """Test force flag for deletion commands."""
        parser = create_cli()
        
        args = parser.parse_args(['delete-all', '--force'])
        assert args.force is True

        args = parser.parse_args(['delete-all-by-project', 'project-123', '--force'])
        assert args.force is True

        args = parser.parse_args(['delete-nodes', 'project-123', '-f'])
        assert args.force is True


class TestOutputFormatter:
    """Tests for output formatting."""

    def test_format_json(self):
        """Test JSON formatting."""
        data = {'key': 'value', 'number': 42}
        result = OutputFormatter.format_json(data)
        assert '"key": "value"' in result
        assert '"number": 42' in result

    def test_format_result(self):
        """Test result formatting."""
        result = OutputFormatter.format_result(
            'delete-all',
            'project-123',
            100,
            {'message': 'Success'}
        )

        assert result['operation'] == 'delete-all'
        assert result['project_id'] == 'project-123'
        assert result['deleted_count'] == 100
        assert result['success'] is True
        assert result['details']['message'] == 'Success'

    def test_format_error(self):
        """Test error formatting."""
        result = OutputFormatter.format_error('Test error', 'operation')

        assert result['success'] is False
        assert result['error'] == 'Test error'
        assert result['operation'] == 'operation'

    def test_format_status(self):
        """Test status formatting."""
        result = OutputFormatter.format_status('project-123', 50, 30)

        assert result['project_id'] == 'project-123'
        assert result['node_count'] == 50
        assert result['relationship_count'] == 30
        assert result['total_items'] == 80

    def test_format_health(self):
        """Test health check formatting."""
        result = OutputFormatter.format_health(True, 'Healthy')

        assert result['neo4j_healthy'] is True
        assert result['message'] == 'Healthy'

    @patch('builtins.print')
    def test_print_output_dict(self, mock_print):
        """Test printing dict output."""
        OutputFormatter.print_output({'key': 'value'}, json_output=True)
        mock_print.assert_called_once()
        assert '"key": "value"' in mock_print.call_args[0][0]

    @patch('builtins.print')
    def test_print_output_string(self, mock_print):
        """Test printing string output."""
        OutputFormatter.print_output('Test message')
        mock_print.assert_called_once_with('Test message')

    @patch('builtins.print')
    def test_print_output_quiet(self, mock_print):
        """Test quiet mode suppresses string output."""
        OutputFormatter.print_output('Test message', quiet=True)
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_print_output_json_string(self, mock_print):
        """Test printing JSON string output."""
        OutputFormatter.print_output('{"key": "value"}', json_output=True)
        mock_print.assert_called_once()
        assert '"key": "value"' in mock_print.call_args[0][0]


class TestCreateConfig:
    """Tests for config creation from CLI args."""

    def test_create_config_default(self):
        """Test config creation with defaults."""
        parser = create_cli()
        args = parser.parse_args(['health'])
        config = create_config(args)

        assert config.neo4j_uri == 'bolt://localhost:7687'
        assert config.neo4j_user == 'neo4j'
        assert config.neo4j_password == 'password'

    def test_create_config_custom(self):
        """Test config creation with custom values."""
        parser = create_cli()
        args = parser.parse_args([
            '--neo4j-uri', 'bolt://custom:7687',
            '--neo4j-user', 'customuser',
            '--neo4j-password', 'custompass',
            'health'
        ])
        config = create_config(args)

        assert config.neo4j_uri == 'bolt://custom:7687'
        assert config.neo4j_user == 'customuser'
        assert config.neo4j_password == 'custompass'


class TestRunHealthCheck:
    """Tests for health check command."""

    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_health_check_healthy(self, mock_manager_class):
        """Test healthy connection."""
        mock_manager = MagicMock()
        mock_manager.health_check.return_value = True
        mock_manager_class.return_value = mock_manager

        parser = create_cli()
        args = parser.parse_args(['health'])

        result = run_health_check(args)

        assert result == 0
        mock_manager.health_check.assert_called_once()
        mock_manager.close.assert_called_once()

    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_health_check_unhealthy(self, mock_manager_class):
        """Test unhealthy connection."""
        mock_manager = MagicMock()
        mock_manager.health_check.return_value = False
        mock_manager_class.return_value = mock_manager

        parser = create_cli()
        args = parser.parse_args(['health'])

        result = run_health_check(args)

        assert result == 1

    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_health_check_error(self, mock_manager_class):
        """Test health check error."""
        mock_manager_class.side_effect = Neo4jConnectionError('Connection failed')

        parser = create_cli()
        args = parser.parse_args(['health'])

        result = run_health_check(args)

        assert result == 1

    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_health_check_unexpected_error(self, mock_manager_class):
        """Test unexpected health check error."""
        mock_manager_class.side_effect = RuntimeError('boom')

        parser = create_cli()
        args = parser.parse_args(['health'])

        result = run_health_check(args)

        assert result == 1


class TestRunStatus:
    """Tests for status command."""

    @patch('codeminer.database.cli.GraphStorage')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_status_success(self, mock_manager_class, mock_storage_class):
        """Test status command success."""
        from codeminer.database.models import GraphSummary

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_storage = MagicMock()
        mock_storage.get_summary.return_value = GraphSummary(
            total_nodes=50,
            nodes_by_type={'Class': 10, 'Method': 40},
            total_relationships=30,
            relationships_by_type={'CONTAINS': 20, 'CALLS': 10}
        )
        mock_storage_class.return_value = mock_storage

        parser = create_cli()
        args = parser.parse_args(['status', 'project-123'])

        result = run_status(args)

        assert result == 0
        mock_storage.get_summary.assert_called_once_with('project-123')

    @patch('codeminer.database.cli.GraphStorage')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_status_error(self, mock_manager_class, mock_storage_class):
        """Test status command error."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_storage = MagicMock()
        mock_storage.get_summary.side_effect = GraphStorageError('Query failed')
        mock_storage_class.return_value = mock_storage

        parser = create_cli()
        args = parser.parse_args(['status', 'project-123'])

        result = run_status(args)

        assert result == 1

    @patch('codeminer.database.cli.GraphStorage')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_status_unexpected_error(self, mock_manager_class, mock_storage_class):
        """Test status command unexpected error."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_storage = MagicMock()
        mock_storage.get_summary.side_effect = RuntimeError('boom')
        mock_storage_class.return_value = mock_storage

        parser = create_cli()
        args = parser.parse_args(['status', 'project-123'])

        result = run_status(args)

        assert result == 1


class TestRunDeleteAll:
    """Tests for delete-all command."""

    @patch('codeminer.database.cli.delete_all_graph_data')
    def test_delete_all_force(self, mock_delete):
        """Test delete-all with force flag."""
        mock_delete.return_value = 150

        parser = create_cli()
        args = parser.parse_args(['delete-all', '--force'])

        result = run_delete_all(args)

        assert result == 0
        mock_delete.assert_called_once()

    @patch('codeminer.database.cli.delete_all_graph_data')
    def test_delete_all_dry_run(self, mock_delete):
        """Test delete-all with dry-run."""
        parser = create_cli()
        args = parser.parse_args(['--dry-run', 'delete-all'])

        result = run_delete_all(args)

        assert result == 0
        mock_delete.assert_not_called()

    @patch('codeminer.database.cli.confirm_deletion', return_value=False)
    def test_delete_all_cancelled(self, mock_confirm):
        """Test delete-all cancelled by user."""
        parser = create_cli()
        args = parser.parse_args(['delete-all'])

        result = run_delete_all(args)

        assert result == 0

    @patch('codeminer.database.cli.delete_all_graph_data')
    def test_delete_all_error(self, mock_delete):
        """Test delete-all error."""
        mock_delete.side_effect = GraphStorageError('Deletion failed')

        parser = create_cli()
        args = parser.parse_args(['delete-all', '--force'])

        result = run_delete_all(args)

        assert result == 1

    @patch('codeminer.database.cli.delete_all_graph_data')
    def test_delete_all_unexpected_error(self, mock_delete):
        """Test delete-all unexpected error."""
        mock_delete.side_effect = RuntimeError('boom')

        parser = create_cli()
        args = parser.parse_args(['delete-all', '--force'])

        result = run_delete_all(args)

        assert result == 1


class TestRunDeleteAllByProject:
    """Tests for delete-all-by-project command."""

    @patch('codeminer.database.cli.delete_all_graph_data_by_project')
    def test_delete_all_by_project_force(self, mock_delete):
        """Test project-scoped delete-all with force flag."""
        mock_delete.return_value = 150

        parser = create_cli()
        args = parser.parse_args(['delete-all-by-project', 'project-123', '--force'])

        result = run_delete_all_by_project(args)

        assert result == 0
        mock_delete.assert_called_once()

    @patch('codeminer.database.cli.delete_all_graph_data_by_project')
    def test_delete_all_by_project_dry_run(self, mock_delete):
        """Test project-scoped delete-all with dry-run."""
        parser = create_cli()
        args = parser.parse_args(['--dry-run', 'delete-all-by-project', 'project-123'])

        result = run_delete_all_by_project(args)

        assert result == 0
        mock_delete.assert_not_called()

    @patch('codeminer.database.cli.confirm_deletion', return_value=False)
    def test_delete_all_by_project_cancelled(self, mock_confirm):
        """Test project-scoped delete-all cancelled by user."""
        parser = create_cli()
        args = parser.parse_args(['delete-all-by-project', 'project-123'])

        result = run_delete_all_by_project(args)

        assert result == 0

    @patch('codeminer.database.cli.delete_all_graph_data_by_project')
    def test_delete_all_by_project_error(self, mock_delete):
        """Test project-scoped delete-all error."""
        mock_delete.side_effect = GraphStorageError('Deletion failed')

        parser = create_cli()
        args = parser.parse_args(['delete-all-by-project', 'project-123', '--force'])

        result = run_delete_all_by_project(args)

        assert result == 1

    @patch('codeminer.database.cli.delete_all_graph_data_by_project')
    def test_delete_all_by_project_unexpected_error(self, mock_delete):
        """Test project-scoped delete-all unexpected error."""
        mock_delete.side_effect = RuntimeError('boom')

        parser = create_cli()
        args = parser.parse_args(['delete-all-by-project', 'project-123', '--force'])

        result = run_delete_all_by_project(args)

        assert result == 1


class TestRunDeleteNodes:
    """Tests for delete-nodes command."""

    @patch('codeminer.database.cli.delete_nodes_only')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_delete_nodes_force(self, mock_manager_class, mock_delete):
        """Test delete-nodes with force flag."""
        mock_delete.return_value = 100

        parser = create_cli()
        args = parser.parse_args(['delete-nodes', 'project-123', '--force'])

        result = run_delete_nodes(args)

        assert result == 0
        mock_delete.assert_called_once()

    @patch('codeminer.database.cli.delete_nodes_only')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_delete_nodes_dry_run(self, mock_manager_class, mock_delete):
        """Test delete-nodes with dry-run."""
        parser = create_cli()
        args = parser.parse_args(['--dry-run', 'delete-nodes', 'project-123'])

        result = run_delete_nodes(args)

        assert result == 0
        mock_delete.assert_not_called()

    @patch('codeminer.database.cli.confirm_deletion', return_value=False)
    def test_delete_nodes_cancelled(self, mock_confirm):
        """Test delete-nodes cancelled by user."""
        parser = create_cli()
        args = parser.parse_args(['delete-nodes', 'project-123'])

        result = run_delete_nodes(args)

        assert result == 0

    @patch('codeminer.database.cli.delete_nodes_only')
    def test_delete_nodes_error(self, mock_delete):
        """Test delete-nodes graph storage error."""
        mock_delete.side_effect = GraphStorageError('Deletion failed')

        parser = create_cli()
        args = parser.parse_args(['delete-nodes', 'project-123', '--force'])

        result = run_delete_nodes(args)

        assert result == 1

    @patch('codeminer.database.cli.delete_nodes_only')
    def test_delete_nodes_unexpected_error(self, mock_delete):
        """Test delete-nodes unexpected error."""
        mock_delete.side_effect = RuntimeError('boom')

        parser = create_cli()
        args = parser.parse_args(['delete-nodes', 'project-123', '--force'])

        result = run_delete_nodes(args)

        assert result == 1


class TestRunDeleteRelationships:
    """Tests for delete-relationships command."""

    @patch('codeminer.database.cli.delete_relationships_only')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_delete_relationships_force(self, mock_manager_class, mock_delete):
        """Test delete-relationships with force flag."""
        mock_delete.return_value = 50

        parser = create_cli()
        args = parser.parse_args(['delete-relationships', 'project-123', '--force'])

        result = run_delete_relationships(args)

        assert result == 0
        mock_delete.assert_called_once()

    @patch('codeminer.database.cli.confirm_deletion', return_value=False)
    def test_delete_relationships_cancelled(self, mock_confirm):
        """Test delete-relationships cancelled by user."""
        parser = create_cli()
        args = parser.parse_args(['delete-relationships', 'project-123'])

        result = run_delete_relationships(args)

        assert result == 0

    @patch('codeminer.database.cli.delete_relationships_only')
    def test_delete_relationships_dry_run(self, mock_delete):
        """Test delete-relationships with dry-run."""
        parser = create_cli()
        args = parser.parse_args(['--dry-run', 'delete-relationships', 'project-123'])

        result = run_delete_relationships(args)

        assert result == 0
        mock_delete.assert_not_called()

    @patch('codeminer.database.cli.delete_relationships_only')
    def test_delete_relationships_error(self, mock_delete):
        """Test delete-relationships graph storage error."""
        mock_delete.side_effect = GraphStorageError('Deletion failed')

        parser = create_cli()
        args = parser.parse_args(['delete-relationships', 'project-123', '--force'])

        result = run_delete_relationships(args)

        assert result == 1

    @patch('codeminer.database.cli.delete_relationships_only')
    def test_delete_relationships_unexpected_error(self, mock_delete):
        """Test delete-relationships unexpected error."""
        mock_delete.side_effect = RuntimeError('boom')

        parser = create_cli()
        args = parser.parse_args(['delete-relationships', 'project-123', '--force'])

        result = run_delete_relationships(args)

        assert result == 1


class TestRunDeleteNodesByType:
    """Tests for delete-nodes-by-type command."""

    @patch('codeminer.database.cli.delete_nodes_by_type')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_delete_nodes_by_type(self, mock_manager_class, mock_delete):
        """Test delete-nodes-by-type success."""
        mock_delete.return_value = 30

        parser = create_cli()
        args = parser.parse_args([
            'delete-nodes-by-type', 'project-123',
            '--types', 'Method', 'Function',
            '--force'
        ])

        result = run_delete_nodes_by_type(args)

        assert result == 0
        mock_delete.assert_called_once()

    @patch('codeminer.database.cli.confirm_deletion', return_value=False)
    def test_delete_nodes_by_type_cancelled(self, mock_confirm):
        """Test delete-nodes-by-type cancelled by user."""
        parser = create_cli()
        args = parser.parse_args(['delete-nodes-by-type', 'project-123', '--types', 'Method'])

        result = run_delete_nodes_by_type(args)

        assert result == 0

    @patch('codeminer.database.cli.delete_nodes_by_type')
    def test_delete_nodes_by_type_dry_run(self, mock_delete):
        """Test delete-nodes-by-type with dry-run."""
        parser = create_cli()
        args = parser.parse_args(['--dry-run', 'delete-nodes-by-type', 'project-123', '--types', 'Method'])

        result = run_delete_nodes_by_type(args)

        assert result == 0
        mock_delete.assert_not_called()

    @patch('codeminer.database.cli.delete_nodes_by_type')
    def test_delete_nodes_by_type_error(self, mock_delete):
        """Test delete-nodes-by-type graph storage error."""
        mock_delete.side_effect = GraphStorageError('Deletion failed')

        parser = create_cli()
        args = parser.parse_args(['delete-nodes-by-type', 'project-123', '--types', 'Method', '--force'])

        result = run_delete_nodes_by_type(args)

        assert result == 1

    @patch('codeminer.database.cli.delete_nodes_by_type')
    def test_delete_nodes_by_type_unexpected_error(self, mock_delete):
        """Test delete-nodes-by-type unexpected error."""
        mock_delete.side_effect = RuntimeError('boom')

        parser = create_cli()
        args = parser.parse_args(['delete-nodes-by-type', 'project-123', '--types', 'Method', '--force'])

        result = run_delete_nodes_by_type(args)

        assert result == 1


class TestRunDeleteRelationshipsByType:
    """Tests for delete-relationships-by-type command."""

    @patch('codeminer.database.cli.delete_relationships_by_type')
    @patch('codeminer.database.cli.Neo4jConnectionManager')
    def test_delete_relationships_by_type(self, mock_manager_class, mock_delete):
        """Test delete-relationships-by-type success."""
        mock_delete.return_value = 20

        parser = create_cli()
        args = parser.parse_args([
            'delete-relationships-by-type', 'project-123',
            '--types', 'CALLS',
            '--force'
        ])

        result = run_delete_relationships_by_type(args)

        assert result == 0
        mock_delete.assert_called_once()

    @patch('codeminer.database.cli.confirm_deletion', return_value=False)
    def test_delete_relationships_by_type_cancelled(self, mock_confirm):
        """Test delete-relationships-by-type cancelled by user."""
        parser = create_cli()
        args = parser.parse_args(['delete-relationships-by-type', 'project-123', '--types', 'CALLS'])

        result = run_delete_relationships_by_type(args)

        assert result == 0

    @patch('codeminer.database.cli.delete_relationships_by_type')
    def test_delete_relationships_by_type_dry_run(self, mock_delete):
        """Test delete-relationships-by-type with dry-run."""
        parser = create_cli()
        args = parser.parse_args(['--dry-run', 'delete-relationships-by-type', 'project-123', '--types', 'CALLS'])

        result = run_delete_relationships_by_type(args)

        assert result == 0
        mock_delete.assert_not_called()

    @patch('codeminer.database.cli.delete_relationships_by_type')
    def test_delete_relationships_by_type_error(self, mock_delete):
        """Test delete-relationships-by-type graph storage error."""
        mock_delete.side_effect = GraphStorageError('Deletion failed')

        parser = create_cli()
        args = parser.parse_args(['delete-relationships-by-type', 'project-123', '--types', 'CALLS', '--force'])

        result = run_delete_relationships_by_type(args)

        assert result == 1

    @patch('codeminer.database.cli.delete_relationships_by_type')
    def test_delete_relationships_by_type_unexpected_error(self, mock_delete):
        """Test delete-relationships-by-type unexpected error."""
        mock_delete.side_effect = RuntimeError('boom')

        parser = create_cli()
        args = parser.parse_args(['delete-relationships-by-type', 'project-123', '--types', 'CALLS', '--force'])

        result = run_delete_relationships_by_type(args)

        assert result == 1


class TestRunCommand:
    """Tests for main command dispatcher."""

    def test_run_command_no_command(self):
        """Test running with no command."""
        parser = create_cli()
        args = parser.parse_args([])

        result = run_command(args)

        assert result == 1

    def test_run_command_unknown_command(self):
        """Test running unknown command."""
        args = argparse.Namespace(command='unknown')
        result = run_command(args)

        assert result == 1

    @patch('codeminer.database.cli.run_health_check')
    def test_run_command_health(self, mock_health):
        """Test running health command."""
        mock_health.return_value = 0

        parser = create_cli()
        args = parser.parse_args(['health'])

        result = run_command(args)

        assert result == 0
        mock_health.assert_called_once()

    @patch('codeminer.database.cli.run_delete_all_by_project')
    def test_run_command_delete_all_by_project(self, mock_handler):
        """Test dispatcher routes delete-all-by-project."""
        mock_handler.return_value = 0

        parser = create_cli()
        args = parser.parse_args(['delete-all-by-project', 'project-123', '--force'])

        result = run_command(args)

        assert result == 0
        mock_handler.assert_called_once_with(args)


class TestMain:
    """Tests for CLI entrypoint."""

    @patch('codeminer.database.cli.sys.exit')
    @patch('codeminer.database.cli.run_command', return_value=0)
    @patch('codeminer.database.cli.create_cli')
    def test_main_exits_with_run_command_status(self, mock_create_cli, mock_run_command, mock_exit):
        """Test main parses args and exits with the command status."""
        mock_parser = MagicMock()
        mock_args = argparse.Namespace(command='health')
        mock_parser.parse_args.return_value = mock_args
        mock_create_cli.return_value = mock_parser

        from codeminer.database.cli import main

        main()

        mock_run_command.assert_called_once_with(mock_args)
        mock_exit.assert_called_once_with(0)


class TestConfirmDeletion:
    """Tests for confirmation prompt."""

    @patch('builtins.input', return_value='y')
    def test_confirm_yes(self, mock_input):
        """Test confirming with yes."""
        result = confirm_deletion('all nodes', 'project-123')
        assert result is True

    @patch('builtins.input', return_value='n')
    def test_confirm_no(self, mock_input):
        """Test cancelling with no."""
        result = confirm_deletion('all nodes', 'project-123')
        assert result is False

    @patch('builtins.input', return_value='')
    def test_confirm_empty(self, mock_input):
        """Test cancelling with empty input."""
        result = confirm_deletion('all nodes', 'project-123')
        assert result is False

    @patch('builtins.input', side_effect=['invalid', 'y'])
    def test_confirm_retry(self, mock_input):
        """Test retry on invalid input."""
        result = confirm_deletion('all nodes', 'project-123')
        assert result is True
        assert mock_input.call_count == 2

    @patch('builtins.input', return_value='y')
    def test_confirm_yes_without_project(self, mock_input):
        """Test confirming a global deletion prompt."""
        result = confirm_deletion('all nodes and relationships')
        assert result is True
