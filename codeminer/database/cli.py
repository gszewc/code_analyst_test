"""
CLI interface for Neo4j database cleanup.

This module provides command-line interface for cleaning up Neo4j graph data
including deleting nodes and relationships by project ID.
"""

import argparse
import sys
import json
from typing import Optional, List

from .models import DatabaseConfig
from .graph_cleanup import (
    delete_all_graph_data,
    delete_nodes_only,
    delete_relationships_only,
    delete_nodes_by_type,
    delete_all_graph_data_by_project,
    delete_relationships_by_type,
    GraphCleanup,
)
from .neo4j_manager import Neo4jConnectionManager, Neo4jConnectionError
from .graph_storage import GraphStorage, GraphStorageError


def create_cli() -> argparse.ArgumentParser:
    """
    Create CLI argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='neo4j-cleanup',
        description='Neo4j Database Cleanup Utility',
        epilog='Examples:\n'
               '  neo4j-cleanup delete-all\n'
               '  neo4j-cleanup delete-all-by-project project-123\n'
               '  neo4j-cleanup delete-nodes project-123\n'
               '  neo4j-cleanup delete-relationships project-123\n'
               '  neo4j-cleanup delete-nodes-by-type project-123 --types Method Function\n'
               '  neo4j-cleanup delete-relationships-by-type project-123 --types CALLS DEPENDS_ON\n'
               '  neo4j-cleanup status project-123\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options
    parser.add_argument(
        '--neo4j-uri',
        default='bolt://localhost:7687',
        help='Neo4j Bolt URI (default: bolt://localhost:7687)'
    )

    parser.add_argument(
        '--neo4j-user',
        default='neo4j',
        help='Neo4j username (default: neo4j)'
    )

    parser.add_argument(
        '--neo4j-password',
        default='password',
        help='Neo4j password (default: password)'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode (only show errors)'
    )

    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output in JSON format'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        title='commands',
        description='Available cleanup commands',
        help='Cleanup command to execute'
    )

    # delete-all command
    delete_all_parser = subparsers.add_parser(
        'delete-all',
        help='Delete all nodes and relationships from graph (all projects!!!)'
    )
    delete_all_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip confirmation prompt'
    )
    # delete-all command
    delete_all_by_project_parser = subparsers.add_parser(
        'delete-all-by-project',
        help='Delete all nodes and relationships for a project'
    )
    delete_all_by_project_parser.add_argument(
        'project_id',
        help='Project UUID to delete data for'
    )
    delete_all_by_project_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip confirmation prompt'
    )

    # delete-nodes command
    delete_nodes_parser = subparsers.add_parser(
        'delete-nodes',
        help='Delete only nodes for a project (relationships auto-deleted)'
    )
    delete_nodes_parser.add_argument(
        'project_id',
        help='Project UUID to delete data for'
    )
    delete_nodes_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip confirmation prompt'
    )

    # delete-relationships command
    delete_rels_parser = subparsers.add_parser(
        'delete-relationships',
        help='Delete only relationships for a project (nodes preserved)'
    )
    delete_rels_parser.add_argument(
        'project_id',
        help='Project UUID to delete data for'
    )
    delete_rels_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip confirmation prompt'
    )

    # delete-nodes-by-type command
    delete_nodes_type_parser = subparsers.add_parser(
        'delete-nodes-by-type',
        help='Delete nodes of specific type(s) for a project'
    )
    delete_nodes_type_parser.add_argument(
        'project_id',
        help='Project UUID to delete data for'
    )
    delete_nodes_type_parser.add_argument(
        '--types', '-t',
        nargs='+',
        required=True,
        help='Node types to delete (e.g., Method Function Class)'
    )
    delete_nodes_type_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip confirmation prompt'
    )

    # delete-relationships-by-type command
    delete_rels_type_parser = subparsers.add_parser(
        'delete-relationships-by-type',
        help='Delete relationships of specific type(s) for a project'
    )
    delete_rels_type_parser.add_argument(
        'project_id',
        help='Project UUID to delete data for'
    )
    delete_rels_type_parser.add_argument(
        '--types', '-t',
        nargs='+',
        required=True,
        help='Relationship types to delete (e.g., CALLS DEPENDS_ON CONTAINS)'
    )
    delete_rels_type_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip confirmation prompt'
    )

    # status command
    status_parser = subparsers.add_parser(
        'status',
        help='Get graph statistics for a project'
    )
    status_parser.add_argument(
        'project_id',
        help='Project UUID to get statistics for'
    )

    # health command
    health_parser = subparsers.add_parser(
        'health',
        help='Check Neo4j connection health'
    )

    return parser


class OutputFormatter:
    """Format output for CLI."""

    @staticmethod
    def format_json(data: dict) -> str:
        """Format data as JSON."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def format_result(
        operation: str,
        project_id: str,
        deleted_count: int,
        details: Optional[dict] = None
    ) -> dict:
        """Format deletion result."""
        result = {
            'operation': operation,
            'project_id': project_id,
            'deleted_count': deleted_count,
            'success': True
        }
        if details:
            result['details'] = details
        return result

    @staticmethod
    def format_error(message: str, operation: Optional[str] = None) -> dict:
        """Format error message."""
        return {
            'operation': operation,
            'success': False,
            'error': message
        }

    @staticmethod
    def format_status(project_id: str, node_count: int, relationship_count: int) -> dict:
        """Format status information."""
        return {
            'project_id': project_id,
            'node_count': node_count,
            'relationship_count': relationship_count,
            'total_items': node_count + relationship_count
        }

    @staticmethod
    def format_health(healthy: bool, message: str) -> dict:
        """Format health check result."""
        return {
            'neo4j_healthy': healthy,
            'message': message
        }

    @staticmethod
    def print_output(output, quiet: bool = False, json_output: bool = False):
        """Print output to stdout."""
        if quiet and not isinstance(output, dict):
            return

        if isinstance(output, dict) or json_output:
            if isinstance(output, str):
                output = json.loads(output)
            print(json.dumps(output, indent=2, default=str))
        else:
            print(output)


def confirm_deletion(operation: str, project_id: str = None, types: Optional[List[str]] = None) -> bool:
    """
    Prompt user for confirmation before deletion.

    Args:
        operation: Type of deletion operation
        project_id: Project UUID
        types: Optional list of types to delete

    Returns:
        True if user confirms, False otherwise
    """
    type_info = f" of type(s) {', '.join(types)}" if types else ""
    if project_id:
        print(f"\n⚠️  WARNING: This will delete {operation}{type_info} for project '{project_id}'")
    else:
        print(f"\n⚠️  WARNING: This will delete {operation}{type_info}")
    print("   This action cannot be undone!\n")

    while True:
        response = input("Are you sure you want to continue? [y/N]: ").strip().lower()
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no', ''):
            return False
        else:
            print("Please enter 'y' or 'n'")


def create_config(args: argparse.Namespace) -> DatabaseConfig:
    """Create DatabaseConfig from CLI arguments."""
    return DatabaseConfig(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password
    )


def run_health_check(args: argparse.Namespace) -> int:
    """Run Neo4j health check."""
    try:
        config = create_config(args)
        manager = Neo4jConnectionManager(config)
        healthy = manager.health_check()
        manager.close()

        output = OutputFormatter.format_health(
            healthy,
            "Neo4j connection is healthy" if healthy else "Neo4j connection failed"
        )

        OutputFormatter.print_output(output, args.quiet, args.json)

        return 0 if healthy else 1

    except Neo4jConnectionError as e:
        output = OutputFormatter.format_health(False, str(e))
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_health(False, f"Unexpected error: {e}")
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1


def run_status(args: argparse.Namespace) -> int:
    """Get graph status for a project."""
    try:
        config = create_config(args)
        manager = Neo4jConnectionManager(config)
        storage = GraphStorage(manager)

        # Get summary
        summary = storage.get_summary(args.project_id)
        manager.close()

        output = {
            'project_id': args.project_id,
            'total_nodes': summary.total_nodes,
            'nodes_by_type': summary.nodes_by_type,
            'total_relationships': summary.total_relationships,
            'relationships_by_type': summary.relationships_by_type
        }

        OutputFormatter.print_output(output, args.quiet, args.json)
        return 0

    except GraphStorageError as e:
        output = OutputFormatter.format_error(str(e), 'status')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_error(f"Unexpected error: {e}", 'status')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1


def run_delete_all(args: argparse.Namespace) -> int:
    """Delete all graph data!!!!"""
    try:
        # Confirm deletion
        if not args.force and not args.dry_run:
            if not confirm_deletion('all nodes and relationships'):
                if not args.quiet:
                    print("Operation cancelled.")
                return 0

        if args.dry_run:
            output = {
                'operation': 'delete-all',
                'project_id': 'All projects!!!',
                'dry_run': True,
                'message': 'Would delete all nodes and relationships for this project'
            }
            OutputFormatter.print_output(output, args.quiet, args.json)
            return 0

        config = create_config(args)
        deleted = delete_all_graph_data(config=config)

        output = OutputFormatter.format_result(
            'delete-all',
            'All projects!!!',
            deleted,
            {'message': 'All nodes and relationships deleted'}
        )

        OutputFormatter.print_output(output, args.quiet, args.json)
        return 0

    except GraphStorageError as e:
        output = OutputFormatter.format_error(str(e), 'delete-all')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_error(f"Unexpected error: {e}", 'delete-all')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1

def run_delete_all_by_project(args: argparse.Namespace) -> int:
    """Delete all graph data for a project."""
    try:
        # Confirm deletion
        if not args.force and not args.dry_run:
            if not confirm_deletion('all nodes and relationships', args.project_id):
                if not args.quiet:
                    print("Operation cancelled.")
                return 0

        if args.dry_run:
            output = {
                'operation': 'delete-all',
                'project_id': args.project_id,
                'dry_run': True,
                'message': 'Would delete all nodes and relationships for this project'
            }
            OutputFormatter.print_output(output, args.quiet, args.json)
            return 0

        config = create_config(args)
        deleted = delete_all_graph_data_by_project(args.project_id, config=config)

        output = OutputFormatter.format_result(
            'delete-all',
            args.project_id,
            deleted,
            {'message': 'All nodes and relationships deleted'}
        )

        OutputFormatter.print_output(output, args.quiet, args.json)
        return 0

    except GraphStorageError as e:
        output = OutputFormatter.format_error(str(e), 'delete-all')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_error(f"Unexpected error: {e}", 'delete-all')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1

def run_delete_nodes(args: argparse.Namespace) -> int:
    """Delete only nodes for a project."""
    try:
        # Confirm deletion
        if not args.force and not args.dry_run:
            if not confirm_deletion('all nodes', args.project_id):
                if not args.quiet:
                    print("Operation cancelled.")
                return 0

        if args.dry_run:
            output = {
                'operation': 'delete-nodes',
                'project_id': args.project_id,
                'dry_run': True,
                'message': 'Would delete all nodes (relationships auto-deleted via DETACH)'
            }
            OutputFormatter.print_output(output, args.quiet, args.json)
            return 0

        config = create_config(args)
        deleted = delete_nodes_only(args.project_id, config=config)

        output = OutputFormatter.format_result(
            'delete-nodes',
            args.project_id,
            deleted,
            {'message': 'All nodes deleted (relationships auto-deleted via DETACH)'}
        )

        OutputFormatter.print_output(output, args.quiet, args.json)
        return 0

    except GraphStorageError as e:
        output = OutputFormatter.format_error(str(e), 'delete-nodes')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_error(f"Unexpected error: {e}", 'delete-nodes')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1


def run_delete_relationships(args: argparse.Namespace) -> int:
    """Delete only relationships for a project."""
    try:
        # Confirm deletion
        if not args.force and not args.dry_run:
            if not confirm_deletion('all relationships', args.project_id):
                if not args.quiet:
                    print("Operation cancelled.")
                return 0

        if args.dry_run:
            output = {
                'operation': 'delete-relationships',
                'project_id': args.project_id,
                'dry_run': True,
                'message': 'Would delete all relationships (nodes preserved)'
            }
            OutputFormatter.print_output(output, args.quiet, args.json)
            return 0

        config = create_config(args)
        deleted = delete_relationships_only(args.project_id, config=config)

        output = OutputFormatter.format_result(
            'delete-relationships',
            args.project_id,
            deleted,
            {'message': 'All relationships deleted (nodes preserved)'}
        )

        OutputFormatter.print_output(output, args.quiet, args.json)
        return 0

    except GraphStorageError as e:
        output = OutputFormatter.format_error(str(e), 'delete-relationships')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_error(f"Unexpected error: {e}", 'delete-relationships')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1


def run_delete_nodes_by_type(args: argparse.Namespace) -> int:
    """Delete nodes by type for a project."""
    try:
        # Confirm deletion
        if not args.force and not args.dry_run:
            if not confirm_deletion('nodes', args.project_id, args.types):
                if not args.quiet:
                    print("Operation cancelled.")
                return 0

        if args.dry_run:
            output = {
                'operation': 'delete-nodes-by-type',
                'project_id': args.project_id,
                'types': args.types,
                'dry_run': True,
                'message': f"Would delete nodes of type(s): {', '.join(args.types)}"
            }
            OutputFormatter.print_output(output, args.quiet, args.json)
            return 0

        config = create_config(args)
        deleted = delete_nodes_by_type(args.project_id, args.types, config=config)

        output = OutputFormatter.format_result(
            'delete-nodes-by-type',
            args.project_id,
            deleted,
            {
                'types': args.types,
                'message': f"Deleted nodes of type(s): {', '.join(args.types)}"
            }
        )

        OutputFormatter.print_output(output, args.quiet, args.json)
        return 0

    except GraphStorageError as e:
        output = OutputFormatter.format_error(str(e), 'delete-nodes-by-type')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_error(f"Unexpected error: {e}", 'delete-nodes-by-type')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1


def run_delete_relationships_by_type(args: argparse.Namespace) -> int:
    """Delete relationships by type for a project."""
    try:
        # Confirm deletion
        if not args.force and not args.dry_run:
            if not confirm_deletion('relationships', args.project_id, args.types):
                if not args.quiet:
                    print("Operation cancelled.")
                return 0

        if args.dry_run:
            output = {
                'operation': 'delete-relationships-by-type',
                'project_id': args.project_id,
                'types': args.types,
                'dry_run': True,
                'message': f"Would delete relationships of type(s): {', '.join(args.types)}"
            }
            OutputFormatter.print_output(output, args.quiet, args.json)
            return 0

        config = create_config(args)
        deleted = delete_relationships_by_type(
            args.project_id, args.types, config=config
        )

        output = OutputFormatter.format_result(
            'delete-relationships-by-type',
            args.project_id,
            deleted,
            {
                'types': args.types,
                'message': f"Deleted relationships of type(s): {', '.join(args.types)}"
            }
        )

        OutputFormatter.print_output(output, args.quiet, args.json)
        return 0

    except GraphStorageError as e:
        output = OutputFormatter.format_error(str(e), 'delete-relationships-by-type')
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1
    except Exception as e:
        output = OutputFormatter.format_error(
            f"Unexpected error: {e}", 'delete-relationships-by-type'
        )
        OutputFormatter.print_output(output, args.quiet, args.json)
        return 1


def run_command(args: argparse.Namespace) -> int:
    """
    Run CLI command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if args.command is None:
        print("Error: No command specified. Use --help for usage.")
        return 1

    command_handlers = {
        'delete-all': run_delete_all,
        'delete-all-by-project': run_delete_all_by_project,
        'delete-nodes': run_delete_nodes,
        'delete-relationships': run_delete_relationships,
        'delete-nodes-by-type': run_delete_nodes_by_type,
        'delete-relationships-by-type': run_delete_relationships_by_type,
        'status': run_status,
        'health': run_health_check,
    }

    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"Error: Unknown command '{args.command}'")
        return 1


def main():
    """CLI entry point."""
    parser = create_cli()
    args = parser.parse_args()

    exit_code = run_command(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
