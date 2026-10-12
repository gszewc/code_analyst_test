"""Tests for ModuleRegistry."""

import pytest
from codeminer.parsing.models import ASTNode, NodeType
from codeminer.parsing.python.module_registry import ModuleRegistry, ResolvedImport


def _make_file_node(node_id: str, source_file: str, name: str) -> ASTNode:
    return ASTNode(id=node_id, type=NodeType.FILE.value, name=name, source_file=source_file)


def _make_class_node(node_id: str, source_file: str, name: str) -> ASTNode:
    return ASTNode(id=node_id, type=NodeType.CLASS.value, name=name, source_file=source_file)


def _make_func_node(node_id: str, source_file: str, name: str) -> ASTNode:
    return ASTNode(id=node_id, type=NodeType.FUNCTION.value, name=name, source_file=source_file)


class TestModuleRegistryBuild:
    def test_registers_file_as_module(self):
        nodes = [_make_file_node("f1", "mypackage/utils.py", "utils.py")]
        reg = ModuleRegistry(nodes)
        assert "mypackage.utils" in reg.module_map

    def test_init_py_registers_as_package(self):
        nodes = [_make_file_node("f1", "mypackage/__init__.py", "__init__.py")]
        reg = ModuleRegistry(nodes)
        assert "mypackage" in reg.module_map

    def test_registers_top_level_symbols(self):
        file_node = _make_file_node("f1", "mypackage/utils.py", "utils.py")
        class_node = _make_class_node("c1", "mypackage/utils.py", "ClassA")
        func_node = _make_func_node("fn1", "mypackage/utils.py", "helper_func")
        nodes = [file_node, class_node, func_node]
        reg = ModuleRegistry(nodes)
        assert "mypackage.utils.ClassA" in reg.symbol_map
        assert "mypackage.utils.helper_func" in reg.symbol_map

    def test_prefix_stripping_src(self):
        nodes = [_make_file_node("f1", "src/mypackage/utils.py", "utils.py")]
        reg = ModuleRegistry(nodes)
        assert "mypackage.utils" in reg.module_map

    def test_project_root_file(self):
        nodes = [_make_file_node("f1", "main.py", "main.py")]
        reg = ModuleRegistry(nodes)
        assert "main" in reg.module_map


class TestModuleRegistryResolve:
    def _build_registry(self):
        file_node = _make_file_node("f1", "mypackage/utils.py", "utils.py")
        class_node = _make_class_node("c1", "mypackage/utils.py", "ClassA")
        func_node = _make_func_node("fn1", "mypackage/utils.py", "helper_func")
        init_node = _make_file_node("f2", "mypackage/__init__.py", "__init__.py")
        return ModuleRegistry([file_node, class_node, func_node, init_node])

    def test_resolve_absolute_module(self):
        reg = self._build_registry()
        results = reg.resolve("mypackage.utils", ["ClassA"], "other/file.py", level=0)
        assert len(results) == 1
        assert results[0].target_file_node_id == "f1"
        assert results[0].target_symbol_node_id == "c1"
        assert results[0].is_external is False

    def test_resolve_absolute_function(self):
        reg = self._build_registry()
        results = reg.resolve("mypackage.utils", ["helper_func"], "other/file.py", level=0)
        assert results[0].target_symbol_node_id == "fn1"

    def test_resolve_external_returns_is_external(self):
        reg = self._build_registry()
        results = reg.resolve("pandas", ["DataFrame"], "file.py", level=0)
        assert len(results) == 1
        assert results[0].is_external is True
        assert results[0].target_file_node_id is None

    def test_resolve_relative_import(self):
        reg = self._build_registry()
        results = reg.resolve("utils", ["ClassA"], "mypackage/main.py", level=1)
        assert len(results) == 1
        assert results[0].target_symbol_node_id == "c1"

    def test_resolve_bare_import(self):
        """import foo.bar → module-level DEPENDS_ON, no symbol."""
        reg = self._build_registry()
        results = reg.resolve("mypackage.utils", ["mypackage.utils"], "other.py", level=0)
        assert len(results) == 1
        assert results[0].target_file_node_id == "f1"

    def test_resolve_from_dot_import(self):
        """from . import X where module is None."""
        file_node = _make_file_node("f1", "mypackage/utils.py", "utils.py")
        x_node = _make_func_node("fn1", "mypackage/utils.py", "X")
        init_node = _make_file_node("f2", "mypackage/__init__.py", "__init__.py")
        reg = ModuleRegistry([file_node, x_node, init_node])
        results = reg.resolve(None, ["X"], "mypackage/sub.py", level=1)
        assert len(results) >= 1

    def test_resolve_star_import(self):
        """from module import * → should handle gracefully."""
        reg = self._build_registry()
        results = reg.resolve("mypackage.utils", ["*"], "other.py", level=0)
        assert len(results) == 1  # file-level only

    def test_resolve_multiple_names(self):
        reg = self._build_registry()
        results = reg.resolve("mypackage.utils", ["ClassA", "helper_func"], "other.py", level=0)
        assert len(results) == 2

    def test_prefix_stripped_resolution(self):
        """src/mypackage/utils.py should resolve via 'mypackage.utils'."""
        file_node = _make_file_node("f1", "src/mypackage/utils.py", "utils.py")
        class_node = _make_class_node("c1", "src/mypackage/utils.py", "ClassA")
        reg = ModuleRegistry([file_node, class_node])
        results = reg.resolve("mypackage.utils", ["ClassA"], "src/other.py", level=0)
        assert len(results) == 1
        assert results[0].is_external is False
