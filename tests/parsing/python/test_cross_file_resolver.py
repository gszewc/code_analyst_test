"""Tests for CrossFileResolver."""

import pytest
from codeminer.parsing.models import (
    ASTNode, ASTResult, FileInfo, Relationship, RelationshipType, NodeType,
    CrossFileConfig, RawImport, UnresolvedReference, Summary,
)
from codeminer.parsing.python.cross_file_resolver import CrossFileResolver


def _file(node_id, source_file, name):
    return ASTNode(id=node_id, type=NodeType.FILE.value, name=name, source_file=source_file)


def _cls(node_id, source_file, name, base_classes=None):
    return ASTNode(id=node_id, type=NodeType.CLASS.value, name=name, source_file=source_file, base_classes=base_classes)


def _func(node_id, source_file, name):
    return ASTNode(id=node_id, type=NodeType.FUNCTION.value, name=name, source_file=source_file)


def _method(node_id, source_file, name):
    return ASTNode(id=node_id, type=NodeType.METHOD.value, name=name, source_file=source_file)


def _var(node_id, source_file, name):
    return ASTNode(id=node_id, type=NodeType.VARIABLE.value, name=name, source_file=source_file)


def _rel(src, tgt, rtype):
    return Relationship(source_id=src, target_id=tgt, type=rtype)


def _make_ast_result(nodes, relationships=None, raw_imports=None, unresolved_references=None):
    return ASTResult(
        file_info=FileInfo(path="/test", name="test", is_directory=True),
        nodes=nodes,
        relationships=relationships or [],
        raw_imports=raw_imports or [],
        unresolved_references=unresolved_references or [],
        summary=Summary(),
    )


class TestStage2Imports:
    """Stage 2: Import resolution → DEPENDS_ON + IMPORTS relationships."""

    def test_creates_depends_on(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _cls("c1", "mypackage/utils.py", "ClassA"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["ClassA"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, new_nodes = resolver.resolve(ast_result)

        depends_on = [r for r in new_rels if r.type == RelationshipType.DEPENDS_ON.value]
        assert len(depends_on) == 1
        assert depends_on[0].source_id == "f1"
        assert depends_on[0].target_id == "f2"

    def test_creates_imports_relationship(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _cls("c1", "mypackage/utils.py", "ClassA"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["ClassA"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, new_nodes = resolver.resolve(ast_result)

        imports = [r for r in new_rels if r.type == RelationshipType.IMPORTS.value]
        assert len(imports) == 1
        assert imports[0].source_id == "f1"
        assert imports[0].target_id == "c1"

    def test_depends_on_deduplicated(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _cls("c1", "mypackage/utils.py", "ClassA"),
            _func("fn1", "mypackage/utils.py", "helper"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["ClassA", "helper"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, _ = resolver.resolve(ast_result)

        depends_on = [r for r in new_rels if r.type == RelationshipType.DEPENDS_ON.value]
        assert len(depends_on) == 1  # deduplicated

    def test_imports_disabled_no_relationships(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _cls("c1", "mypackage/utils.py", "ClassA"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["ClassA"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        config = CrossFileConfig(imports=False)
        resolver = CrossFileResolver(config)
        new_rels, _ = resolver.resolve(ast_result)

        depends_on = [r for r in new_rels if r.type == RelationshipType.DEPENDS_ON.value]
        imports = [r for r in new_rels if r.type == RelationshipType.IMPORTS.value]
        assert len(depends_on) == 0
        assert len(imports) == 0

    def test_star_import_creates_depends_on_only(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["*"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, _ = resolver.resolve(ast_result)

        depends_on = [r for r in new_rels if r.type == RelationshipType.DEPENDS_ON.value]
        imports = [r for r in new_rels if r.type == RelationshipType.IMPORTS.value]
        assert len(depends_on) == 1
        assert len(imports) == 0


class TestStage2ExternalModules:
    def test_external_module_created_when_enabled(self):
        nodes = [_file("f1", "app/main.py", "main.py")]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="pandas", names=["DataFrame"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        config = CrossFileConfig(include_external=True)
        resolver = CrossFileResolver(config)
        new_rels, new_nodes = resolver.resolve(ast_result)

        ext_nodes = [n for n in new_nodes if n.type == NodeType.EXTERNAL_MODULE.value]
        assert len(ext_nodes) == 1
        assert ext_nodes[0].name == "pandas"
        assert ext_nodes[0].source_file == ""
        assert ext_nodes[0].start_line == 0

    def test_external_module_skipped_when_disabled(self):
        nodes = [_file("f1", "app/main.py", "main.py")]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="pandas", names=["DataFrame"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        config = CrossFileConfig(include_external=False)
        resolver = CrossFileResolver(config)
        _, new_nodes = resolver.resolve(ast_result)

        assert len(new_nodes) == 0


class TestStage3Inheritance:
    def test_cross_file_extends(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _cls("c_child", "app/main.py", "Child", base_classes=["BaseClass"]),
            _file("f2", "mypackage/base.py", "base.py"),
            _cls("c_base", "mypackage/base.py", "BaseClass"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.base", names=["BaseClass"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, _ = resolver.resolve(ast_result)

        extends = [r for r in new_rels if r.type == RelationshipType.EXTENDS.value]
        assert len(extends) == 1
        assert extends[0].source_id == "c_child"
        assert extends[0].target_id == "c_base"

    def test_inheritance_disabled(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _cls("c_child", "app/main.py", "Child", base_classes=["BaseClass"]),
            _file("f2", "mypackage/base.py", "base.py"),
            _cls("c_base", "mypackage/base.py", "BaseClass"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.base", names=["BaseClass"], level=0,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports)

        config = CrossFileConfig(inheritance=False)
        resolver = CrossFileResolver(config)
        new_rels, _ = resolver.resolve(ast_result)

        extends = [r for r in new_rels if r.type == RelationshipType.EXTENDS.value]
        assert len(extends) == 0


class TestStage4CallsAndUsage:
    def test_cross_file_call(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _func("fn_caller", "app/main.py", "caller"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _func("fn_helper", "mypackage/utils.py", "helper_func"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["helper_func"], level=0,
        )]
        unresolved = [UnresolvedReference(
            source_file="app/main.py", source_node_id="fn_caller",
            reference_name="helper_func", reference_type="call", line=5,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports, unresolved_references=unresolved)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, _ = resolver.resolve(ast_result)

        calls = [r for r in new_rels if r.type == RelationshipType.CALLS.value]
        assert len(calls) == 1
        assert calls[0].source_id == "fn_caller"
        assert calls[0].target_id == "fn_helper"

    def test_cross_file_dotted_call(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _func("fn_caller", "app/main.py", "caller"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _cls("c1", "mypackage/utils.py", "ClassA"),
            _method("m1", "mypackage/utils.py", "method"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        rels = [_rel("c1", "m1", RelationshipType.CONTAINS.value)]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["ClassA"], level=0,
        )]
        unresolved = [UnresolvedReference(
            source_file="app/main.py", source_node_id="fn_caller",
            reference_name="ClassA.method", reference_type="call", line=5,
        )]
        ast_result = _make_ast_result(nodes, rels, raw_imports=raw_imports, unresolved_references=unresolved)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, _ = resolver.resolve(ast_result)

        calls = [r for r in new_rels if r.type == RelationshipType.CALLS.value]
        assert len(calls) == 1
        assert calls[0].target_id == "m1"

    def test_calls_disabled(self):
        nodes = [
            _file("f1", "app/main.py", "main.py"),
            _func("fn_caller", "app/main.py", "caller"),
            _file("f2", "mypackage/utils.py", "utils.py"),
            _func("fn_helper", "mypackage/utils.py", "helper_func"),
            _file("f3", "mypackage/__init__.py", "__init__.py"),
        ]
        raw_imports = [RawImport(
            source_file="app/main.py", source_file_node_id="f1",
            module="mypackage.utils", names=["helper_func"], level=0,
        )]
        unresolved = [UnresolvedReference(
            source_file="app/main.py", source_node_id="fn_caller",
            reference_name="helper_func", reference_type="call", line=5,
        )]
        ast_result = _make_ast_result(nodes, raw_imports=raw_imports, unresolved_references=unresolved)

        config = CrossFileConfig(calls=False)
        resolver = CrossFileResolver(config)
        new_rels, _ = resolver.resolve(ast_result)

        calls = [r for r in new_rels if r.type == RelationshipType.CALLS.value]
        assert len(calls) == 0


class TestEmptyProject:
    def test_no_imports_no_new_relationships(self):
        nodes = [_file("f1", "main.py", "main.py")]
        ast_result = _make_ast_result(nodes)

        resolver = CrossFileResolver(CrossFileConfig())
        new_rels, new_nodes = resolver.resolve(ast_result)

        assert len(new_rels) == 0
        assert len(new_nodes) == 0
