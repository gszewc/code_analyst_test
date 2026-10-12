"""
CLI interface for AST Parser.

This module provides command-line interface for the AST Parser.
"""

import argparse
import json
import sys
from typing import Optional

from codeminer.parsing.models import ASTResult
from .ast_parser import ASTParser
from .utils import logger


def create_cli() -> argparse.ArgumentParser:
    """
    Create CLI argument parser.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='parser-cli',
        description='AST Parser for Python source code',
        epilog='Examples:\n'
               '  parser-cli parse file.py\n'
               '  parser-cli parse-dir /path/to/project\n'
               '  parser-cli summary file.py\n'
               '  parser-cli export file.py -o output.json\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'command',
        choices=['parse', 'parse-dir', 'summary', 'export'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'path',
        help='File or directory path to parse'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode (only show errors)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Show only summary statistics'
    )
    
    parser.add_argument(
        '--base-dir',
        help='Base directory for path validation (default: current directory)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for directory parsing (default: 10)'
    )
    
    return parser


class OutputFormatter:
    """Format ASTResult for output."""
    
    @staticmethod
    def format_json(result: ASTResult, pretty: bool = True) -> str:
        """
        Format result as JSON.
        
        Args:
            result: ASTResult to format
            pretty: Whether to pretty-print
            
        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(result.model_dump(), indent=2, default=str)
        return json.dumps(result.model_dump(), default=str)
    
    @staticmethod
    def format_summary(result: ASTResult) -> str:
        """
        Format summary statistics.
        
        Args:
            result: ASTResult with summary
            
        Returns:
            Formatted summary string
        """
        summary = result.summary
        lines = [
            f"Files: {summary.total_files}",
            f"Nodes: {summary.total_nodes}",
            f"  by type: {summary.nodes_by_type}",
            f"Relationships: {summary.total_relationships}",
            f"  by type: {summary.relationships_by_type}",
            f"Errors: {summary.total_errors}",
            f"Duration: {summary.parsing_duration_ms/1000:.2f}s"
        ]
        return '\n'.join(lines)
    
    @staticmethod
    def write_output(content: str, output_path: Optional[str] = None):
        """
        Write output to stdout or file.
        
        Args:
            content: Content to write
            output_path: File path (None for stdout)
        """
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(content)


def run_command(args: argparse.Namespace) -> int:
    """
    Run CLI command.
    
    Args:
        args: Parsed arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Create parser
    base_dir = args.base_dir if args.base_dir else None
    parser = ASTParser(base_dir=base_dir)
    
    # Execute command
    try:
        if args.command == 'parse':
            result = parser.parse_file(args.path)
        elif args.command == 'parse-dir':
            result = parser.parse_directory(args.path, batch_size=args.batch_size)
        elif args.command == 'summary':
            result = parser.parse_file(args.path) if args.path.endswith('.py') else parser.parse_directory(args.path)
        elif args.command == 'export':
            result = parser.parse_file(args.path)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
        
        # Format output
        if args.summary_only or args.command == 'summary':
            output = OutputFormatter.format_summary(result)
        else:
            output = OutputFormatter.format_json(result, pretty=not args.quiet)
        
        # Write output
        OutputFormatter.write_output(output, args.output)
        
        # Log summary
        if not args.quiet:
            logger.info(f"Complete: {result.summary.total_files} files, "
                       f"{result.summary.total_nodes} nodes, "
                       f"{result.summary.total_errors} errors")
        
        return 0 if not result.errors else 1
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """CLI entry point."""
    parser = create_cli()
    args = parser.parse_args()
    
    # Run command
    exit_code = run_command(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
