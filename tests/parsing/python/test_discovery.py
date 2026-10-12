"""Tests for FileDiscovery component."""

import os
import pytest
from pathlib import Path

from codeminer.parsing.python.discovery_legacy import FileDiscovery


class TestFileDiscovery:
    """Test FileDiscovery functionality."""
    
    def test_discover_files_single_file(self, tmp_path):
        """Test discovering a single Python file."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def func(): pass")
        
        files = FileDiscovery.discover_files(str(tmp_path))
        
        assert len(files) == 1
        assert str(test_file) in files
    
    def test_discover_files_directory(self, tmp_path):
        """Test discovering multiple Python files in directory."""
        # Create test files
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("def func2(): pass")
        (tmp_path / "file3.txt").write_text("not python")
        
        files = FileDiscovery.discover_files(str(tmp_path))
        
        assert len(files) == 2
        assert all(f.endswith('.py') for f in files)
    
    def test_discover_files_excludes_directories(self, tmp_path):
        """Test that excluded directories are skipped."""
        # Create excluded directories
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / "venv").mkdir()
        (tmp_path / "node_modules").mkdir()
        
        # Create files in excluded directories
        (tmp_path / "__pycache__" / "cache.py").write_text("pass")
        (tmp_path / ".git" / "config.py").write_text("pass")
        (tmp_path / "venv" / "script.py").write_text("pass")
        
        # Create file in main directory
        (tmp_path / "main.py").write_text("pass")
        
        files = FileDiscovery.discover_files(str(tmp_path))
        
        assert len(files) == 1
        assert files[0].endswith("main.py")
    
    def test_discover_files_excludes_hidden_directories(self, tmp_path):
        """Test that hidden directories are skipped."""
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.py").write_text("pass")
        (tmp_path / "visible.py").write_text("pass")
        
        files = FileDiscovery.discover_files(str(tmp_path))
        
        assert len(files) == 1
        assert files[0].endswith("visible.py")
    
    def test_discover_files_excludes_init_py(self, tmp_path):
        """Test that __init__.py files are excluded."""
        (tmp_path / "__init__.py").write_text("pass")
        (tmp_path / "module.py").write_text("pass")
        
        files = FileDiscovery.discover_files(str(tmp_path))
        
        assert len(files) == 1
        assert not files[0].endswith("__init__.py")
    
    def test_discover_files_no_python_files(self, tmp_path):
        """Test discovering when no Python files exist."""
        (tmp_path / "file.txt").write_text("text")
        (tmp_path / "file.md").write_text("markdown")
        
        files = FileDiscovery.discover_files(str(tmp_path))
        
        assert len(files) == 0
    
    def test_should_include_file(self):
        """Test file inclusion logic."""
        assert FileDiscovery.should_include_file("test.py") is True
        assert FileDiscovery.should_include_file("__init__.py") is False
        assert FileDiscovery.should_include_file("test.txt") is False
        assert FileDiscovery.should_include_file("test.pyc") is False
    
    def test_should_include_directory(self):
        """Test directory inclusion logic."""
        assert FileDiscovery.should_include_directory("src") is True
        assert FileDiscovery.should_include_directory("__pycache__") is False
        assert FileDiscovery.should_include_directory(".git") is False
        assert FileDiscovery.should_include_directory("venv") is False
        assert FileDiscovery.should_include_directory(".hidden") is False
