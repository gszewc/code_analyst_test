"""Pytest fixtures for AST Parser tests."""

import os
import pytest


@pytest.fixture
def fixtures_dir():
    """Return the path to the fixtures directory."""
    return os.path.join(os.path.dirname(__file__), 'fixtures')
