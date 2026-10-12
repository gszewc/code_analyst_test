import os
import pytest
from unittest.mock import MagicMock
from codeminer.parsing.discovery import FileDiscovery
from codeminer.parsing.registry import ParserRegistry


def _make_stub_parser(name, extensions, excluded_dirs=None):
    parser = MagicMock()
    parser.get_language_name.return_value = name
    parser.get_supported_extensions.return_value = extensions
    parser.get_excluded_dirs.return_value = excluded_dirs or set()
    return parser


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temp project with mixed files."""
    (tmp_path / "main.py").write_text("x = 1")
    (tmp_path / "App.java").write_text("class App {}")
    (tmp_path / "readme.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "helper.py").write_text("y = 2")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.py").write_text("z = 3")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("")
    return tmp_path


def test_discover_groups_by_language(tmp_project):
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    reg.register(_make_stub_parser("java", [".java"]))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(tmp_project))

    assert "python" in result
    assert "java" in result
    py_names = [os.path.basename(f) for f in result["python"]]
    assert "main.py" in py_names
    assert "helper.py" in py_names
    assert "cached.py" not in py_names  # excluded __pycache__
    java_names = [os.path.basename(f) for f in result["java"]]
    assert "App.java" in java_names


def test_discover_filters_by_language(tmp_project):
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    reg.register(_make_stub_parser("java", [".java"]))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(tmp_project), languages=["python"])

    assert "python" in result
    assert "java" not in result


def test_discover_filters_by_folders(tmp_project):
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(tmp_project), folders=["sub"])

    py_names = [os.path.basename(f) for f in result.get("python", [])]
    assert "helper.py" in py_names
    assert "main.py" not in py_names


def test_discover_nonexistent_folder_ignored(tmp_project):
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(tmp_project), folders=["nonexistent"])
    assert result.get("python", []) == []


def test_discover_excludes_git_and_node_modules(tmp_project):
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"]))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(tmp_project))
    all_files = [f for files in result.values() for f in files]
    assert not any(".git" in f for f in all_files)


# ---------------------------------------------------------------------------
# Symlink discovery tests (US2)
# ---------------------------------------------------------------------------


@pytest.fixture
def symlink_project(tmp_path, require_symlinks):
    """Project root with a symlinked directory."""
    # External directory (outside project root)
    external = tmp_path / "external_lib"
    external.mkdir()
    (external / "utils.py").write_text("def helper(): pass")
    (external / "constants.py").write_text("X = 42")

    # Project root
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("import utils")

    # Symlink inside project pointing to external dir
    (project / "lib").symlink_to(external)

    return project


def test_discover_follows_symlinked_directory(symlink_project):
    """Discovery should include files reachable through a symlinked directory."""
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(symlink_project))

    py_names = [os.path.basename(f) for f in result.get("python", [])]
    assert "main.py" in py_names
    assert "utils.py" in py_names
    assert "constants.py" in py_names


def test_discover_symlinked_files_use_alias_paths(symlink_project):
    """Files behind a symlink should appear under the alias path, not the real path."""
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(symlink_project))

    paths = result.get("python", [])
    # Alias paths should start with symlink_project (project root)
    assert all(p.startswith(str(symlink_project)) for p in paths)
    # No path should start with the external directory
    external = str(symlink_project.parent / "external_lib")
    assert not any(p.startswith(external) for p in paths)


def test_discover_folder_filter_works_through_symlink(symlink_project):
    """Folder filters should match paths that traverse symlinked segments."""
    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    discovery = FileDiscovery(reg)

    result = discovery.discover_files(str(symlink_project), folders=["lib"])

    py_names = [os.path.basename(f) for f in result.get("python", [])]
    assert "utils.py" in py_names
    assert "constants.py" in py_names
    assert "main.py" not in py_names


def test_discover_cycle_detection_terminates(tmp_path, require_symlinks):
    """Discovery must terminate safely when symlinks create a cycle."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("x = 1")

    # Create a cycle: project/loop -> project
    (project / "loop").symlink_to(project)

    reg = ParserRegistry()
    reg.register(_make_stub_parser("python", [".py"], {"__pycache__"}))
    discovery = FileDiscovery(reg)

    # Should complete without hanging or infinite recursion
    result = discovery.discover_files(str(project))

    py_names = [os.path.basename(f) for f in result.get("python", [])]
    assert "main.py" in py_names

