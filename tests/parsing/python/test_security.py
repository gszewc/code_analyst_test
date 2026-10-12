"""Tests for SecurityValidator component."""

import os
import pytest
from pathlib import Path

from codeminer.parsing.security import SecurityValidator
from codeminer.parsing.python.path_normalization import (
    PathNormalizationError,
    normalize_source_file_path,
)


class TestSecurityValidator:
    """Test SecurityValidator functionality."""
    
    def test_validate_path_valid(self, tmp_path):
        """Test validation of valid path within base directory."""
        base_dir = str(tmp_path)
        valid_path = str(tmp_path / "subdir" / "file.py")
        
        # Create the path
        os.makedirs(os.path.dirname(valid_path), exist_ok=True)
        Path(valid_path).touch()
        
        is_valid, resolved = SecurityValidator.validate_path(valid_path, base_dir)
        
        assert is_valid is True
        assert resolved == os.path.realpath(valid_path)
    
    def test_validate_path_traversal_detected(self, tmp_path):
        """Test that directory traversal is detected."""
        base_dir = str(tmp_path / "allowed")
        base_dir_sub = str(tmp_path / "allowed" / "subdir")
        os.makedirs(base_dir_sub, exist_ok=True)
        
        # Try to escape with ..
        traversal_path = os.path.join(base_dir_sub, ".." , ".." , "etc" , "passwd")
        
        is_valid, resolved = SecurityValidator.validate_path(traversal_path, base_dir)
        
        assert is_valid is False
    
    def test_validate_path_symlink_resolved(self, tmp_path):
        """Test that symlinks are resolved."""
        base_dir = str(tmp_path)
        
        # Create a file and a symlink
        real_file = tmp_path / "real.py"
        real_file.write_text("pass")
        
        link_file = tmp_path / "link.py"
        try:
            link_file.symlink_to(real_file)
            
            is_valid, resolved = SecurityValidator.validate_path(str(link_file), base_dir)
            
            assert is_valid is True
            assert resolved == os.path.realpath(str(link_file))
        except (OSError, NotImplementedError):
            # Symlinks not supported on this system
            pytest.skip("Symlinks not supported")
    
    def test_validate_path_outside_base(self, tmp_path):
        """Test that paths outside base directory are rejected."""
        base_dir = str(tmp_path / "base")
        os.makedirs(base_dir, exist_ok=True)
        
        outside_path = str(tmp_path / "other" / "file.py")
        os.makedirs(os.path.dirname(outside_path), exist_ok=True)
        Path(outside_path).touch()
        
        is_valid, resolved = SecurityValidator.validate_path(outside_path, base_dir)
        
        assert is_valid is False
    
    def test_validate_path_base_dir_itself(self, tmp_path):
        """Test that base directory itself is valid."""
        base_dir = str(tmp_path)
        
        is_valid, resolved = SecurityValidator.validate_path(base_dir, base_dir)
        
        assert is_valid is True
        assert resolved == os.path.realpath(base_dir)

    def test_normalize_source_file_path_outside_root_raises(self, tmp_path):
        """Out-of-root source path should raise PathNormalizationError."""
        root = tmp_path / "uploads" / "project-1" / "source"
        root.mkdir(parents=True)
        outside = tmp_path / "uploads" / "project-1" / "outside.py"
        outside.write_text("print('x')", encoding="utf-8")

        with pytest.raises(PathNormalizationError):
            normalize_source_file_path(str(outside), str(root))

    def test_normalize_source_file_path_empty_inputs_raise(self):
        """Malformed empty normalization inputs should raise explicit errors."""
        with pytest.raises(PathNormalizationError):
            normalize_source_file_path("", "/tmp/project")

        with pytest.raises(PathNormalizationError):
            normalize_source_file_path("/tmp/project/file.py", "")


# ---------------------------------------------------------------------------
# Alias path tests (US2) — symlink-aware normalization and security
# ---------------------------------------------------------------------------


class TestAliasPathNormalization:
    """Test that normalize_source_file_path preserves alias paths through symlinks."""

    def test_alias_path_within_root_normalized(self, tmp_path):
        """A regular file path within root normalizes correctly."""
        root = tmp_path / "source"
        root.mkdir()
        f = root / "sub" / "file.py"
        f.parent.mkdir()
        f.write_text("x = 1")

        result = normalize_source_file_path(str(f), str(root))
        assert result == "sub/file.py"

    def test_alias_path_through_symlink_to_external(self, tmp_path, require_symlinks):
        """Alias path through an in-project symlink pointing outside root is preserved."""
        external = tmp_path / "external"
        external.mkdir()
        (external / "utils.py").write_text("pass")

        root = tmp_path / "source"
        root.mkdir()
        # linked_dir is a symlink inside root pointing to external
        (root / "linked_dir").symlink_to(external)

        # The alias path is root/linked_dir/utils.py (not the realpath)
        alias_file = root / "linked_dir" / "utils.py"

        result = normalize_source_file_path(str(alias_file), str(root))
        assert result == "linked_dir/utils.py"

    def test_traversal_path_outside_root_rejected(self, tmp_path):
        """A path that escapes root without going through a symlink is rejected."""
        root = tmp_path / "source"
        root.mkdir()
        outside = tmp_path / "other" / "file.py"
        outside.parent.mkdir()
        outside.write_text("x = 1")

        with pytest.raises(PathNormalizationError):
            normalize_source_file_path(str(outside), str(root))


class TestValidateAliasPath:
    """Test SecurityValidator.validate_alias_path()."""

    def test_valid_relative_path_within_root(self, tmp_path):
        root = tmp_path / "source"
        root.mkdir()
        (root / "app.py").write_text("x = 1")

        is_valid, alias = SecurityValidator.validate_alias_path(
            str(root / "app.py"), str(root)
        )
        assert is_valid is True
        assert alias == "app.py"

    def test_traversal_using_dotdot_rejected(self, tmp_path):
        root = tmp_path / "source"
        root.mkdir()

        traversal = str(root / ".." / "etc" / "passwd")
        is_valid, _ = SecurityValidator.validate_alias_path(traversal, str(root))
        assert is_valid is False

    def test_alias_path_through_symlink_to_external_allowed(self, tmp_path, require_symlinks):
        """An in-project symlink to an external directory should be allowed."""
        external = tmp_path / "external"
        external.mkdir()
        (external / "config.py").write_text("X = 1")

        root = tmp_path / "source"
        root.mkdir()
        (root / "ext").symlink_to(external)

        alias = str(root / "ext" / "config.py")
        is_valid, rel = SecurityValidator.validate_alias_path(alias, str(root))
        assert is_valid is True
        assert rel == "ext/config.py"

    def test_path_not_rooted_in_project_rejected(self, tmp_path):
        root = tmp_path / "source"
        root.mkdir()
        outside = tmp_path / "other" / "file.py"
        outside.parent.mkdir()
        outside.write_text("x = 1")

        is_valid, _ = SecurityValidator.validate_alias_path(str(outside), str(root))
        assert is_valid is False

