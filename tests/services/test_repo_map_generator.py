"""Unit tests for RepoMapGenerator."""

import logging

import pytest
from pathlib import Path

from codeminer.parsing.models import ASTNode
from codeminer.services.repo_map_generator import RepoMapGenerator


def make_node(
    node_id, node_type, name, source_file,
    start_line=1, end_line=1, signature=None, decorators=None,
):
    return ASTNode(
        id=node_id,
        type=node_type,
        name=name,
        source_file=source_file,
        start_line=start_line,
        end_line=end_line,
        signature=signature,
        decorators=decorators,
    )


class TestRepoMapGeneratorRender:
    def setup_method(self):
        self.gen = RepoMapGenerator()

    def test_empty_nodes_produces_header(self):
        result = self.gen._render([])
        assert result == "# Repository map (no nodes found)\n"

    def test_files_sorted_alphabetically(self):
        nodes = [
            make_node("1", "Function", "b_func", "b.py", 1, 5, "def b_func():"),
            make_node("2", "Function", "a_func", "a.py", 1, 5, "def a_func():"),
        ]
        result = self.gen._render(nodes)
        assert result.index("a.py:") < result.index("b.py:")

    def test_nodes_within_file_sorted_by_start_line(self):
        nodes = [
            make_node("1", "Function", "later", "f.py", 10, 15, "def later():"),
            make_node("2", "Function", "earlier", "f.py", 1, 5, "def earlier():"),
        ]
        result = self.gen._render(nodes)
        assert result.index("earlier") < result.index("later")

    def test_blank_line_after_each_file_block(self):
        nodes = [
            make_node("1", "Function", "f", "a.py", 1, 3, "def f():"),
            make_node("2", "Function", "g", "b.py", 1, 3, "def g():"),
        ]
        lines = self.gen._render(nodes).split("\n")
        a_idx = next(i for i, ln in enumerate(lines) if ln == "a.py:")
        # a.py: → │def f(): → blank line
        assert lines[a_idx + 2] == ""

    def test_node_with_no_signature_is_skipped(self):
        nodes = [
            make_node("1", "Class", "MyClass", "f.py", 1, 10, None),
            make_node("2", "Function", "func", "f.py", 12, 15, "def func():"),
        ]
        result = self.gen._render(nodes)
        assert "MyClass" not in result
        assert "│def func():" in result

    def test_function_line_prefixed_with_pipe(self):
        nodes = [make_node("1", "Function", "foo", "f.py", 1, 3, "def foo(x, y):")]
        result = self.gen._render(nodes)
        assert "│def foo(x, y):" in result

    def test_method_indented_inside_class(self):
        nodes = [
            make_node("c", "Class", "MyClass", "f.py", 1, 20, "class MyClass:"),
            make_node("m", "Method", "run", "f.py", 5, 10, "def run(self):"),
        ]
        result = self.gen._render(nodes)
        assert "│    def run(self):" in result

    def test_top_level_function_not_indented(self):
        nodes = [make_node("1", "Function", "top", "f.py", 1, 5, "def top():")]
        result = self.gen._render(nodes)
        assert "│def top():" in result

    def test_multiline_signature_each_line_prefixed(self):
        sig = "def method(\n    self,\n    arg,\n):"
        nodes = [
            make_node("c", "Class", "C", "f.py", 1, 20, "class C:"),
            make_node("m", "Method", "method", "f.py", 2, 10, sig),
        ]
        result = self.gen._render(nodes)
        assert "│    def method(" in result
        assert "│        self," in result
        assert "│        arg," in result

    def test_decorator_emitted_before_def(self):
        nodes = [
            make_node("c", "Class", "C", "f.py", 1, 20, "class C:"),
            make_node("m", "Method", "m", "f.py", 2, 5, "def m(self):", decorators=["classmethod"]),
        ]
        lines = self.gen._render(nodes).split("\n")
        dec_idx = next(i for i, ln in enumerate(lines) if "@classmethod" in ln)
        def_idx = next(i for i, ln in enumerate(lines) if "def m(self):" in ln)
        assert dec_idx < def_idx

    def test_non_map_types_excluded(self):
        nodes = [
            make_node("1", "File", "f.py", "f.py", 1, 100, "f.py"),
            make_node("2", "Import", "os", "f.py", 1, 1, "import os"),
            make_node("3", "Module", "mod", "f.py", 1, 1, "mod"),
            make_node("4", "Function", "func", "f.py", 5, 10, "def func():"),
        ]
        result = self.gen._render(nodes)
        assert "│import os" not in result
        assert "│def func():" in result

    def test_multilanguage_nodes_both_rendered(self):
        nodes = [
            make_node("1", "Class", "PyClass", "src/a.py", 1, 10, "class PyClass:"),
            make_node("2", "Class", "JavaClass", "src/B.java", 1, 10, "public class B {"),
        ]
        result = self.gen._render(nodes)
        assert "src/a.py:" in result
        assert "src/B.java:" in result

    def test_class_header_not_indented(self):
        nodes = [make_node("c", "Class", "C", "f.py", 1, 20, "class C:")]
        result = self.gen._render(nodes)
        assert "│class C:" in result
        assert "│    class C:" not in result

    def test_file_with_all_nodes_missing_signatures_omitted(self):
        """If every node in a file has no signature, that file is omitted from output."""
        nodes = [
            make_node("1", "Class", "NoSig", "f.py", 1, 10, None),
            make_node("2", "Method", "also_no_sig", "f.py", 2, 5, None),
        ]
        result = self.gen._render(nodes)
        assert "f.py:" not in result
        assert result == "# Repository map (no nodes found)\n"

    def test_signatureless_class_does_not_indent_its_methods(self):
        """Methods inside a class with no signature must NOT be indented (class won't render)."""
        nodes = [
            make_node("c", "Class", "Ghost", "f.py", 1, 20, None),   # no signature
            make_node("m", "Method", "run", "f.py", 5, 10, "def run(self):"),
        ]
        result = self.gen._render(nodes)
        assert "│def run(self):" in result      # not indented
        assert "│    def run(self):" not in result  # definitely not indented


class TestRepoMapGeneratorWrite:
    def test_writes_to_output_path(self, tmp_path):
        gen = RepoMapGenerator()
        output = tmp_path / "repomap.txt"
        nodes = [make_node("1", "Function", "f", "a.py", 1, 3, "def f():")]
        gen.generate(nodes, output)
        assert output.exists()
        assert "│def f():" in output.read_text()

    def test_write_failure_logged_not_raised(self, tmp_path, caplog):
        gen = RepoMapGenerator()
        bad_path = tmp_path / "no_such_dir" / "repomap.txt"
        nodes = [make_node("1", "Function", "f", "a.py", 1, 3, "def f():")]
        with caplog.at_level(logging.ERROR, logger="codeminer.services.repo_map_generator"):
            gen.generate(nodes, bad_path)  # must not raise
        assert "Failed to write" in caplog.text
