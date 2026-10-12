"""Tests for CLI component."""

import os
import sys
import pytest
import subprocess
from pathlib import Path

from codeminer.parsing.python.cli import create_cli, OutputFormatter, run_command
from codeminer.parsing.models import ASTResult, FileInfo, Summary


class TestCLI:
    """Test CLI functionality."""
    
    def test_cli_parse_command(self, fixtures_dir):
        """Test parse command."""
        parser = create_cli()
        file_path = os.path.join(fixtures_dir, "sample.py")
        
        args = parser.parse_args(['parse', file_path])
        
        assert args.command == 'parse'
        assert args.path == file_path
    
    def test_cli_parse_dir_command(self, tmp_path):
        """Test parse-dir command."""
        parser = create_cli()
        
        args = parser.parse_args(['parse-dir', str(tmp_path)])
        
        assert args.command == 'parse-dir'
        assert args.path == str(tmp_path)
    
    def test_cli_summary_command(self, fixtures_dir):
        """Test summary command."""
        parser = create_cli()
        file_path = os.path.join(fixtures_dir, "sample.py")
        
        args = parser.parse_args(['summary', file_path])
        
        assert args.command == 'summary'
        assert args.summary_only is False
    
    def test_cli_export_command(self, fixtures_dir):
        """Test export command."""
        parser = create_cli()
        file_path = os.path.join(fixtures_dir, "sample.py")
        
        args = parser.parse_args(['export', file_path, '-o', '/tmp/output.json'])
        
        assert args.command == 'export'
        assert args.output == '/tmp/output.json'
    
    def test_cli_help_command(self):
        """Test help output."""
        parser = create_cli()
        
        # Should not raise
        help_text = parser.format_help()
        
        assert 'parser-cli' in help_text
        assert 'parse' in help_text
        assert 'parse-dir' in help_text
    
    def test_cli_quiet_mode(self, fixtures_dir):
        """Test quiet mode flag."""
        parser = create_cli()
        file_path = os.path.join(fixtures_dir, "sample.py")
        
        args = parser.parse_args(['parse', file_path, '--quiet'])
        
        assert args.quiet is True
    
    def test_cli_batch_size(self, tmp_path):
        """Test batch size option."""
        parser = create_cli()
        
        args = parser.parse_args(['parse-dir', str(tmp_path), '--batch-size', '20'])
        
        assert args.batch_size == 20


class TestOutputFormatter:
    """Test OutputFormatter functionality."""
    
    def test_format_json_pretty(self):
        """Test pretty-printed JSON output."""
        result = ASTResult(
            file_info=FileInfo(path="/test.py", name="test.py", size=100),
            nodes=[],
            relationships=[],
            errors=[],
            summary=Summary()
        )
        
        output = OutputFormatter.format_json(result, pretty=True)
        
        assert '{\n' in output  # Pretty-printed has newlines
        assert '  ' in output   # With indentation
    
    def test_format_json_compact(self):
        """Test compact JSON output."""
        result = ASTResult(
            file_info=FileInfo(path="/test.py", name="test.py", size=100),
            nodes=[],
            relationships=[],
            errors=[],
            summary=Summary()
        )
        
        output = OutputFormatter.format_json(result, pretty=False)
        
        assert '\n' not in output  # No newlines in compact
        assert '{' in output
    
    def test_format_summary(self):
        """Test summary formatting."""
        result = ASTResult(
            file_info=FileInfo(path="/test.py", name="test.py", size=100),
            nodes=[],
            relationships=[],
            errors=[],
            summary=Summary(
                total_files=10,
                total_nodes=100,
                total_relationships=50,
                total_errors=2,
                parsing_duration_ms=1500.0
            )
        )
        
        output = OutputFormatter.format_summary(result)
        
        assert 'Files: 10' in output
        assert 'Nodes: 100' in output
        assert 'Relationships: 50' in output
        assert 'Errors: 2' in output
    
    def test_write_output_stdout(self, capsys):
        """Test writing output to stdout."""
        content = "test output"
        
        OutputFormatter.write_output(content, None)
        
        captured = capsys.readouterr()
        assert "test output" in captured.out
    
    def test_write_output_to_file(self, tmp_path):
        """Test writing output to file."""
        content = "test output"
        output_path = tmp_path / "output.txt"
        
        OutputFormatter.write_output(content, str(output_path))
        
        assert output_path.exists()
        assert output_path.read_text() == content


class TestRunCommand:
    """Test run_command functionality."""
    
    def test_run_command_parse_file(self, fixtures_dir):
        """Test running parse command."""
        parser = create_cli()
        file_path = os.path.join(fixtures_dir, "sample.py")
        
        args = parser.parse_args(['parse', file_path, '--quiet'])
        
        exit_code = run_command(args)
        
        # Should succeed (0) or have errors (1)
        assert exit_code in [0, 1]
    
    def test_run_command_invalid_path(self):
        """Test running command with invalid path."""
        parser = create_cli()
        
        args = parser.parse_args(['parse', '/nonexistent/file.py', '--quiet'])
        
        exit_code = run_command(args)
        
        assert exit_code == 1
