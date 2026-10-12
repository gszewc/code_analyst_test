"""
Utility functions for AST Parser.

This module provides I/O handling, logging configuration, and other utilities.
"""

import logging
import tokenize
import io
import os
from typing import Optional


# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class IOHandler:
    """Handle file I/O operations."""
    
    @staticmethod
    def read_file(file_path: str, encoding: str = None) -> str:
        """
        Read file content with buffered I/O.
        
        Args:
            file_path: Path to file to read
            encoding: File encoding (auto-detected if None)
            
        Returns:
            File content as string
            
        Raises:
            IOError: If file cannot be read
        """
        if encoding is None:
            encoding = IOHandler.detect_encoding(file_path)
        
        with open(file_path, 'r', encoding=encoding, buffering=-1) as f:
            return f.read()
    
    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """
        Auto-detect file encoding using tokenize module.
        
        Args:
            file_path: Path to file
            
        Returns:
            Detected encoding (default: utf-8)
        """
        try:
            with open(file_path, 'rb') as f:
                # tokenize.detect_encoding returns (encoding, first_line)
                encoding, _ = tokenize.detect_encoding(f.readline)
                return encoding
        except (tokenize.TokenError, SyntaxError):
            # Default to utf-8 if detection fails
            return 'utf-8'
    
    @staticmethod
    def write_file(file_path: str, content: str, encoding: str = 'utf-8'):
        """
        Write file content with buffered I/O.
        
        Args:
            file_path: Path to file to write
            content: Content to write
            encoding: File encoding
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding=encoding, buffering=-1) as f:
            f.write(content)
