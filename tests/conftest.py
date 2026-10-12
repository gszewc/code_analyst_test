"""
Root conftest for all tests.

Adds codeminer directory to Python path for all tests.
"""

import sys
import os
import pytest

# Add codeminer directory to Python path - executed first
codeminer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'codeminer'))

def pytest_configure(config):
    """Configure pytest - add codeminer to path."""
    if codeminer_path not in sys.path:
        sys.path.insert(0, codeminer_path)


# ---------------------------------------------------------------------------
# Symlink helpers (Linux-focused)
# ---------------------------------------------------------------------------

def _symlinks_supported(tmp_path) -> bool:
    """Return True if the OS supports symlinks on this filesystem."""
    try:
        link = tmp_path / "_symlink_probe"
        target = tmp_path / "_symlink_target"
        target.touch()
        link.symlink_to(target)
        link.unlink()
        target.unlink()
        return True
    except (OSError, NotImplementedError):
        return False


@pytest.fixture(scope="session")
def symlinks_supported(tmp_path_factory):
    """Session-scoped fixture: True when the OS supports symlinks."""
    return _symlinks_supported(tmp_path_factory.mktemp("probe"))


@pytest.fixture
def require_symlinks(symlinks_supported):
    """Skip the test if symlinks are not supported on this OS/filesystem."""
    if not symlinks_supported:
        pytest.skip("Symlinks not supported on this platform/filesystem")


