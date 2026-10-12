"""Path normalization helpers for AST source_file values."""

from pathlib import Path


class PathNormalizationError(ValueError):
    """Raised when a source path cannot be normalized safely."""


def normalize_source_file_path(file_path: str, project_root: str) -> str:
    """Return a project-relative, POSIX-style source file path.

    Preserves alias paths — that is, paths whose components include in-project
    symlinks that may point outside the physical project root.  The function
    tries a direct string-based ``relative_to`` first (no symlink resolution)
    so that alias identities are retained.  It falls back to resolving both
    paths only when the direct comparison fails (e.g., because project_root
    itself contains symlinks).

    Args:
        file_path: Absolute or relative file path discovered during analysis.
        project_root: Absolute project source root used as normalization boundary.

    Returns:
        Relative path from project_root to file_path using forward slashes.

    Raises:
        PathNormalizationError: If inputs are empty, invalid, or the path cannot
        be made relative to project_root by any of the attempted strategies.
    """
    if not file_path:
        raise PathNormalizationError("file_path cannot be empty")
    if not project_root:
        raise PathNormalizationError("project_root cannot be empty")

    candidate = Path(file_path)
    root = Path(project_root)
    root_resolved = root.resolve()

    # Strategy 1: direct string comparison — preserves alias paths through symlinks.
    for base in (root, root_resolved):
        try:
            relative = candidate.relative_to(base)
            normalized = relative.as_posix()
            if normalized and normalized != ".":
                return normalized
        except ValueError:
            continue

    # Strategy 2: resolve the candidate as well (legacy / non-symlink paths).
    candidate_resolved = candidate.resolve()
    try:
        relative = candidate_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PathNormalizationError(
            f"Path '{file_path}' is outside project root '{project_root}'"
        ) from exc

    normalized = relative.as_posix()
    if normalized in ("", "."):
        raise PathNormalizationError("normalized source file path is invalid")

    return normalized

