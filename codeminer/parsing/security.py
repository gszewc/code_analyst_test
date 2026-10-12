"""
Security validation for AST Parser.

This module provides path validation to prevent directory traversal attacks.
"""

import os
from pathlib import Path


class SecurityValidator:
    """Validate file paths for security."""

    @staticmethod
    def validate_path(requested_path: str, base_dir: str) -> tuple:
        """
        Validate that requested_path is within base_dir.

        Uses os.path.realpath() to resolve symlinks and prevent directory traversal.

        Args:
            requested_path: Path requested by user
            base_dir: Base directory that should contain the path

        Returns:
            Tuple of (is_valid, resolved_path)

        Example:
            >>> is_valid, resolved = SecurityValidator.validate_path(
            ...     "/app_data/../etc/passwd", "/app_data"
            ... )
            >>> is_valid
            False
        """
        # Resolve to absolute path (follows symlinks, resolves ..)
        resolved = os.path.realpath(requested_path)
        base_resolved = os.path.realpath(base_dir)

        # Check if resolved path starts with base directory
        # Add separator to prevent /app_data matching /app_data_other
        if not resolved.startswith(base_resolved + os.sep) and resolved != base_resolved:
            return False, resolved

        return True, resolved

    @staticmethod
    def validate_alias_path(requested_path: str, project_root: str) -> tuple:
        """
        Validate a project-relative alias path.

        Unlike validate_path(), this method does NOT require the resolved
        (realpath) target to be inside project_root.  Instead it verifies:

        1. The path is not absolute.
        2. The path contains no ``..`` traversal components.
        3. The path prefix (before any symlink hop) is rooted inside project_root.

        This allows in-project symlinks to point outside the physical root
        while still blocking raw traversal attempts.

        Args:
            requested_path: Path to validate (may be relative or absolute).
            project_root:   The project source root used as the anchor.

        Returns:
            Tuple of (is_valid, alias_path) where alias_path is the
            project-relative POSIX string on success or the input path on failure.
        """
        project_root_path = Path(project_root).resolve()
        candidate = Path(requested_path)

        # Convert to absolute using project_root if relative
        if not candidate.is_absolute():
            candidate = project_root_path / candidate

        # Reject traversal components
        if ".." in candidate.parts:
            return False, requested_path

        # Verify the path is rooted inside the project tree by checking
        # each component up to (but not including) any symlink that exits root.
        current = project_root_path
        try:
            parts = candidate.relative_to(project_root_path).parts
        except ValueError:
            return False, requested_path

        for part in parts:
            current = current / part
            if current.is_symlink():
                # Once we cross a symlink inside the project tree the remaining
                # path may resolve outside the physical root — that is allowed.
                break
            # Non-symlink component: ensure it hasn't escaped via a plain
            # directory that resolves outside root (handles edge cases).
            resolved_current = current.resolve()
            try:
                resolved_current.relative_to(project_root_path)
            except ValueError:
                return False, requested_path

        try:
            alias_rel = candidate.relative_to(project_root_path).as_posix()
        except ValueError:
            return False, requested_path

        return True, alias_rel

