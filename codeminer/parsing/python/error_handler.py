"""
Error handler for AST Parser.

This module handles parsing errors and creates ParseError objects.
"""

from codeminer.parsing.models import ParseError


class ErrorHandler:
    """Handle parsing errors."""
    
    @staticmethod
    def handle_parse_error(file_path: str, error: Exception) -> ParseError:
        """
        Handle parsing error and return ParseError.
        
        Args:
            file_path: Path to file where error occurred
            error: Exception that was raised
            
        Returns:
            ParseError object
        """
        line_number = None
        message = str(error)
        
        # Extract line number from SyntaxError
        if isinstance(error, SyntaxError):
            line_number = error.lineno
            if error.msg:
                message = f"Syntax error: {error.msg}"
        
        return ParseError(
            file_path=file_path,
            line_number=line_number,
            message=message
        )
    
    @staticmethod
    def handle_encoding_error(file_path: str, error: Exception) -> ParseError:
        """
        Handle encoding error.
        
        Args:
            file_path: Path to file where error occurred
            error: Exception that was raised
            
        Returns:
            ParseError object
        """
        return ParseError(
            file_path=file_path,
            line_number=None,
            message=f"Encoding error: {str(error)}"
        )
    
    @staticmethod
    def handle_io_error(file_path: str, error: Exception) -> ParseError:
        """
        Handle I/O error.
        
        Args:
            file_path: Path to file where error occurred
            error: Exception that was raised
            
        Returns:
            ParseError object
        """
        return ParseError(
            file_path=file_path,
            line_number=None,
            message=f"I/O error: {str(error)}"
        )
    
    @staticmethod
    def should_continue(error: Exception) -> bool:
        """
        Decide whether to continue parsing after an error.
        
        For MVP, always continue (skip failed files).
        
        Args:
            error: Exception that was raised
            
        Returns:
            True if parsing should continue
        """
        # Always continue for MVP
        return True
