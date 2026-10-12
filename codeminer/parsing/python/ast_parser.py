"""
AST Parser for Python source code.

This module provides the main parsing functionality using Python's ast module.
"""

import ast
import time
import os
from typing import Optional

from codeminer.parsing.models import ASTResult, FileInfo, ParseError, Summary
from .discovery_legacy import FileDiscovery
from codeminer.parsing.security import SecurityValidator
from .nodes_visitor import ASTNodeExtractor
from .metrics import MetricsCollector
from .error_handler import ErrorHandler
from .utils import IOHandler, logger


class ASTParser:
    """Parse Python source code and generate AST structures."""

    def __init__(self, base_dir: str = None, skip_path_validation: bool = False):
        """
        Initialize AST Parser.

        Args:
            base_dir: Base directory for path validation (default: current dir)
            skip_path_validation: Skip path validation (for testing)
        """
        self.base_dir = base_dir
        self.skip_path_validation = skip_path_validation
    
    def parse_file(self, file_path: str, project_root: Optional[str] = None) -> ASTResult:
        """
        Parse a single Python file.

        Args:
            file_path: Path to the Python file to parse
            project_root: Optional project upload root used for source_file normalization

        Returns:
            ASTResult containing nodes, relationships, and errors
        """
        start_time = time.perf_counter()
        errors = []
        nodes = []
        relationships = []
        raw_imports = []
        unresolved_references = []

        # Check file exists first (before path validation for non-absolute paths)
        if not os.path.exists(file_path):
            errors.append(ParseError(
                file_path=file_path,
                message=f"File not found: {file_path}"
            ))
            return self._create_empty_result(file_path, errors, start_time)

        # Resolve path for reading — use realpath so open() can follow symlinks,
        # but keep the original alias path for node identity (source_file).
        resolved_path = os.path.realpath(file_path)
        alias_path = file_path  # preserve project-visible alias identity

        # Validate path if base_dir is set and validation is not skipped
        if self.base_dir and not self.skip_path_validation:
            is_valid, resolved_path = SecurityValidator.validate_path(
                resolved_path, self.base_dir
            )
            if not is_valid:
                errors.append(ParseError(
                    file_path=file_path,
                    message=f"Path traversal detected: {file_path}"
                ))
                return self._create_empty_result(file_path, errors, start_time)

        # Read file content
        try:
            content = IOHandler.read_file(resolved_path)
        except Exception as e:
            errors.append(ErrorHandler.handle_io_error(resolved_path, e))
            return self._create_empty_result(file_path, errors, start_time)

        # Parse AST
        try:
            tree = self.parse_source(content, resolved_path)
        except SyntaxError as e:
            errors.append(ErrorHandler.handle_parse_error(resolved_path, e))
            # Continue with partial result
            tree = None
        except Exception as e:
            errors.append(ParseError(
                file_path=resolved_path,
                message=f"Parse error: {str(e)}"
            ))
            return self._create_empty_result(file_path, errors, start_time)

        # Build nodes and detect relationships in single pass
        if tree is not None:
            try:
                normalization_root = project_root or os.path.dirname(resolved_path)
                extractor = ASTNodeExtractor(
                    alias_path,
                    project_root=normalization_root,
                )
                nodes, relationships, raw_imports, unresolved_references = extractor.extract_all(tree)
                if extractor.normalization_errors:
                    errors.extend([
                        ParseError(
                            file_path=alias_path,
                            message=f"Source path normalization failed: {message}",
                        )
                        for message in extractor.normalization_errors
                    ])
                    if project_root is not None:
                        # Reject malformed/out-of-root source paths for project-scoped parsing.
                        nodes = []
                        relationships = []
                        raw_imports = []
                        unresolved_references = []
                    logger.warning(
                        "Source path normalization had %d issue(s) while parsing %s",
                        len(extractor.normalization_errors),
                        alias_path,
                    )
                metrics_collector = MetricsCollector()
                metrics_collector.nodes_created = len(nodes)
                metrics_collector.relationships_created = len(relationships)
            except Exception as e:
                errors.append(ParseError(
                    file_path=alias_path,
                    message=f"Error building nodes: {str(e)}"
                ))
        
        # Create file info
        try:
            stat = os.stat(resolved_path)
            file_info = FileInfo(
                path=resolved_path,
                name=os.path.basename(resolved_path),
                size=stat.st_size,
                language="python",
                last_modified=None,  # Can be added if needed
                is_directory=False,
                file_count=1
            )
        except OSError:
            file_info = FileInfo(
                path=resolved_path,
                name=os.path.basename(resolved_path),
                size=0,
                language="python",
                is_directory=False,
                file_count=1
            )

        # Create summary
        metrics_collector = MetricsCollector()
        summary = metrics_collector.stop(
            start_time,
            total_files=1,
            nodes=nodes,
            relationships=relationships,
            errors=errors
        )
        
        return ASTResult(
            file_info=file_info,
            nodes=nodes,
            relationships=relationships,
            errors=errors,
            summary=summary,
            raw_imports=raw_imports,
            unresolved_references=unresolved_references,
        )

    def parse_source(self, source: str, filename: str = "<unknown>") -> ast.AST:
        """
        Parse source code string.
        
        Args:
            source: Python source code
            filename: Filename for error messages
            
        Returns:
            Parsed AST tree
        """
        return ast.parse(source, filename=filename)
    
    def parse_directory(
        self,
        dir_path: str,
        batch_size: int = 10,
        project_root: Optional[str] = None,
    ) -> ASTResult:
        """
        Parse all Python files in a directory.

        Args:
            dir_path: Path to directory to parse
            batch_size: Number of files to process in each batch
            project_root: Optional project upload root used for source_file normalization

        Returns:
            Combined ASTResult for all files
        """
        start_time = time.perf_counter()
        all_nodes = []
        all_relationships = []
        all_errors = []
        all_raw_imports = []
        all_unresolved_references = []
        files_parsed = 0

        # Check directory exists first
        if not os.path.exists(dir_path):
            all_errors.append(ParseError(
                file_path=dir_path,
                message=f"Directory not found: {dir_path}"
            ))
            return self._create_empty_result(dir_path, all_errors, start_time, is_directory=True)

        # Resolve path
        resolved_path = os.path.realpath(dir_path)

        # Validate path if base_dir is set and validation is not skipped
        if self.base_dir and not self.skip_path_validation:
            is_valid, resolved_path = SecurityValidator.validate_path(
                resolved_path, self.base_dir
            )
            if not is_valid:
                all_errors.append(ParseError(
                    file_path=dir_path,
                    message=f"Path traversal detected: {dir_path}"
                ))
                return self._create_empty_result(dir_path, all_errors, start_time, is_directory=True)

        # Discover files
        files = FileDiscovery.discover_files(resolved_path)

        if not files:
            logger.warning(f"No Python files found in {dir_path}")

        # Process files
        for i, file_path in enumerate(files):
            files_parsed += 1
            logger.info(f"Parsing file {i+1}/{len(files)}: {file_path}")

            normalization_root = project_root or resolved_path
            result = self.parse_file(file_path, project_root=normalization_root)
            all_nodes.extend(result.nodes)
            all_relationships.extend(result.relationships)
            all_errors.extend(result.errors)
            all_raw_imports.extend(result.raw_imports)
            all_unresolved_references.extend(result.unresolved_references)
        
        # Create file info for directory
        file_info = FileInfo(
            path=resolved_path,
            name=os.path.basename(resolved_path),
            size=0,
            language="python",
            is_directory=True,
            file_count=files_parsed
        )

        # Create summary
        metrics_collector = MetricsCollector()
        summary = metrics_collector.stop(
            start_time,
            total_files=files_parsed,
            nodes=all_nodes,
            relationships=all_relationships,
            errors=all_errors
        )
        
        return ASTResult(
            file_info=file_info,
            nodes=all_nodes,
            relationships=all_relationships,
            errors=all_errors,
            summary=summary,
            raw_imports=all_raw_imports,
            unresolved_references=all_unresolved_references,
        )
    
    def _create_empty_result(
        self,
        file_path: str,
        errors: list,
        start_time: float,
        is_directory: bool = False
    ) -> ASTResult:
        """Create an empty ASTResult with errors."""
                
        metrics_collector = MetricsCollector()
        return ASTResult(
            file_info=FileInfo(
                path=file_path,
                name=os.path.basename(file_path),
                size=0,
                language="python",
                is_directory=is_directory,
                file_count=0 if is_directory else 1
            ),
            nodes=[],
            relationships=[],
            errors=errors,
            summary=metrics_collector.stop(
                start_time,
                total_files=0 if is_directory else 1,
                nodes=[],
                relationships=[],
                errors=errors
            )
        )
