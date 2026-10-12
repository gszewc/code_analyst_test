"""
File discovery for AST Parser.

This module provides functionality to discover Python files in directories,
filtering out excluded directories and files.
"""

import os
from typing import List, Set


class FileDiscovery:
    """Discover Python files in directories."""
    
    EXCLUDED_DIRS: Set[str] = {
        '__pycache__',
        '.git',
        'venv',
        'node_modules',
        '.tox'
    }
    
    @staticmethod
    def discover_files(dir_path: str) -> List[str]:
        """
        Recursively discover all .py files in directory.
        
        Args:
            dir_path: Path to directory to search
            
        Returns:
            List of absolute paths to .py files
        """
        result = []
        
        for root, dirs, files in os.walk(dir_path, topdown=True):
            # Filter out excluded directories (modify in-place to prevent descent)
            dirs[:] = [
                d for d in dirs
                if d not in FileDiscovery.EXCLUDED_DIRS and not d.startswith('.')
            ]
            
            # Filter files
            for file in files:
                if FileDiscovery.should_include_file(file, include_initfiles=False):
                    result.append(os.path.join(root, file))
        
        return result
    
    @staticmethod
    def should_include_file(file_name: str, include_initfiles: bool=False) -> bool:
        """
        Check if file should be included in parsing.
        
        Args:
            file_name: Name of the file
            
        Returns:
            True if file should be included
        """
        # Include .py files, exclude __init__.py
        if file_name == '__init__.py':
            return include_initfiles
        return file_name.endswith('.py') and file_name != '__init__.py'
    
    @staticmethod
    def should_include_directory(dir_name: str) -> bool:
        """
        Check if directory should be traversed.
        
        Args:
            dir_name: Name of the directory
            
        Returns:
            True if directory should be traversed
        """
        return (
            dir_name not in FileDiscovery.EXCLUDED_DIRS and
            not dir_name.startswith('.')
        )
