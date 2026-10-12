"""Tests for cross-file dependency data models."""

import pytest
from codeminer.parsing.models import (
    CrossFileConfig,
    RawImport,
    UnresolvedReference,
    NodeType,
    ASTNode,
    ASTResult,
    FileInfo,
)


class TestCrossFileConfig:
    def test_defaults_all_enabled_externals_disabled(self):
        config = CrossFileConfig()
        assert config.imports is True
        assert config.inheritance is True
        assert config.calls is True
        assert config.usage is True
        assert config.include_external is False

    def test_partial_override(self):
        config = CrossFileConfig(imports=False)
        assert config.imports is False
        assert config.inheritance is True  # default kept


class TestRawImport:
    def test_absolute_import(self):
        ri = RawImport(
            source_file="app/main.py",
            source_file_node_id="file-1",
            module="mypackage.utils",
            names=["ClassA", "helper_func"],
            level=0,
        )
        assert ri.module == "mypackage.utils"
        assert ri.level == 0

    def test_relative_import_no_module(self):
        ri = RawImport(
            source_file="app/sub/mod.py",
            source_file_node_id="file-2",
            module=None,
            names=["X"],
            level=1,
        )
        assert ri.module is None
        assert ri.level == 1

    def test_star_import(self):
        ri = RawImport(
            source_file="app/main.py",
            source_file_node_id="file-1",
            module="mypackage.utils",
            names=["*"],
            level=0,
        )
        assert ri.names == ["*"]


class TestUnresolvedReference:
    def test_call_reference(self):
        ref = UnresolvedReference(
            source_file="app/main.py",
            source_node_id="func-1",
            reference_name="ClassA.method",
            reference_type="call",
            line=42,
        )
        assert ref.reference_type == "call"

    def test_usage_reference(self):
        ref = UnresolvedReference(
            source_file="app/main.py",
            source_node_id="func-1",
            reference_name="some_var",
            reference_type="usage",
            line=10,
        )
        assert ref.reference_type == "usage"


class TestNodeTypeExtension:
    def test_external_module_value(self):
        assert NodeType.EXTERNAL_MODULE.value == "ExternalModule"


class TestASTNodeExtension:
    def test_module_path_defaults_none(self):
        node = ASTNode(
            id="test-id",
            type="Import",
            name="os",
            source_file="test.py",
        )
        assert node.module_path is None

    def test_module_path_set(self):
        node = ASTNode(
            id="test-id",
            type="Import",
            name="os",
            source_file="test.py",
            module_path="os.path",
        )
        assert node.module_path == "os.path"


class TestASTResultExtension:
    def test_raw_imports_defaults_empty(self):
        result = ASTResult(
            file_info=FileInfo(path="/test", name="test"),
        )
        assert result.raw_imports == []
        assert result.unresolved_references == []

    def test_raw_imports_populated(self):
        ri = RawImport(
            source_file="test.py",
            source_file_node_id="f1",
            module="os",
            names=["path"],
            level=0,
        )
        result = ASTResult(
            file_info=FileInfo(path="/test", name="test"),
            raw_imports=[ri],
        )
        assert len(result.raw_imports) == 1
