"""Tests for raw import collection in ASTNodeExtractor."""

import ast
import pytest
from codeminer.parsing.python.nodes_visitor import ASTNodeExtractor
from codeminer.parsing.models import RawImport


def _parse(source: str) -> ast.AST:
    return ast.parse(source, filename="<test>")


class TestRawImportCollection:
    """Raw imports must be collected regardless of includeImports flag."""

    def test_absolute_import_collected(self):
        source = "import os"
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 1
        assert raw_imports[0].module == "os"
        assert raw_imports[0].names == ["os"]
        assert raw_imports[0].level == 0

    def test_from_import_collected(self):
        source = "from mypackage.utils import ClassA, helper_func"
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 1
        assert raw_imports[0].module == "mypackage.utils"
        assert raw_imports[0].names == ["ClassA", "helper_func"]
        assert raw_imports[0].level == 0

    def test_relative_import_collected(self):
        source = "from ..utils import helper"
        extractor = ASTNodeExtractor("pkg/sub/mod.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 1
        assert raw_imports[0].module == "utils"
        assert raw_imports[0].level == 2

    def test_relative_import_no_module(self):
        source = "from . import X"
        extractor = ASTNodeExtractor("pkg/mod.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 1
        assert raw_imports[0].module is None
        assert raw_imports[0].names == ["X"]
        assert raw_imports[0].level == 1

    def test_star_import_collected(self):
        source = "from mypackage import *"
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 1
        assert raw_imports[0].names == ["*"]

    def test_import_alias_collected(self):
        source = "import foo.bar as fb"
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 1
        assert raw_imports[0].module == "foo.bar"
        assert raw_imports[0].names == ["foo.bar"]

    def test_include_imports_true_still_collects_raw(self):
        source = "from os import path"
        extractor = ASTNodeExtractor("test.py", includeImports=True)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 1
        # Also should have IMPORT nodes
        import_nodes = [n for n in nodes if n.type == "Import"]
        assert len(import_nodes) >= 1

    def test_imports_dict_populated_when_include_imports_false(self):
        source = "from os import path"
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        extractor.extract_all(_parse(source))
        assert "path" in extractor.get_imports()

    def test_multiple_imports(self):
        source = "import os\nimport sys\nfrom pathlib import Path"
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(raw_imports) == 3

    def test_source_file_node_id_is_file_node(self):
        source = "import os"
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        file_node = [n for n in nodes if n.type == "File"][0]
        assert raw_imports[0].source_file_node_id == file_node.id


class TestExtractAllReturnType:
    def test_returns_four_tuple(self):
        source = "x = 1"
        extractor = ASTNodeExtractor("test.py")
        result = extractor.extract_all(_parse(source))
        assert len(result) == 4

    def test_empty_file_returns_empty_lists(self):
        source = ""
        extractor = ASTNodeExtractor("test.py")
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert raw_imports == []
        assert unresolved == []


class TestUnresolvedReferenceEmission:
    """Calls that can't be resolved within the same file emit UnresolvedReference."""

    def test_unresolved_function_call(self):
        source = """
def my_func():
    unknown_func()
"""
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(unresolved) == 1
        assert unresolved[0].reference_name == "unknown_func"
        assert unresolved[0].reference_type == "call"

    def test_unresolved_method_call(self):
        source = """
def my_func():
    obj.method()
"""
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert len(unresolved) == 1
        assert unresolved[0].reference_name == "obj.method"
        assert unresolved[0].reference_type == "call"

    def test_resolved_call_not_emitted(self):
        source = """
def helper():
    pass

def caller():
    helper()
"""
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        # helper() resolves within same file — should NOT be unresolved
        assert len(unresolved) == 0

    def test_unresolved_reference_has_line_number(self):
        source = """
def my_func():
    unknown_func()
"""
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        assert unresolved[0].line > 0

    def test_unresolved_reference_source_node_is_calling_function(self):
        source = """
def caller():
    unknown()
"""
        extractor = ASTNodeExtractor("test.py", includeImports=False)
        nodes, rels, raw_imports, unresolved = extractor.extract_all(_parse(source))
        caller_node = [n for n in nodes if n.name == "caller"][0]
        assert unresolved[0].source_node_id == caller_node.id
