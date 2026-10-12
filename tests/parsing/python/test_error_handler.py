"""Tests for ErrorHandler component."""

import pytest

from codeminer.parsing.python.error_handler import ErrorHandler
from codeminer.parsing.models import ParseError


class TestErrorHandler:
    """Test ErrorHandler functionality."""
    
    def test_handle_parse_error(self):
        """Test handling a parse error."""
        source = "class Broken\n    pass"
        try:
            compile(source, '<test>', 'exec')
        except SyntaxError as e:
            error = ErrorHandler.handle_parse_error("/test/file.py", e)
            
            assert isinstance(error, ParseError)
            assert error.file_path == "/test/file.py"
            assert error.line_number is not None
            assert "Syntax error" in error.message
    
    def test_handle_encoding_error(self):
        """Test handling an encoding error."""
        error = ErrorHandler.handle_encoding_error(
            "/test/file.py",
            UnicodeDecodeError('utf-8', b'', 0, 1, 'test')
        )
        
        assert isinstance(error, ParseError)
        assert error.file_path == "/test/file.py"
        assert "Encoding error" in error.message
    
    def test_handle_io_error(self):
        """Test handling an I/O error."""
        error = ErrorHandler.handle_io_error(
            "/test/file.py",
            FileNotFoundError("No such file")
        )
        
        assert isinstance(error, ParseError)
        assert error.file_path == "/test/file.py"
        assert "I/O error" in error.message
    
    def test_should_continue(self):
        """Test that parser should continue after errors."""
        # For MVP, should always continue
        assert ErrorHandler.should_continue(Exception("test")) is True
        assert ErrorHandler.should_continue(SyntaxError("test")) is True
        assert ErrorHandler.should_continue(FileNotFoundError("test")) is True
