import os
import tempfile
from codeminer.parsing.python.parser import PythonParser
from codeminer.parsing.interfaces import LanguageParser


def test_python_parser_is_language_parser():
    parser = PythonParser()
    assert isinstance(parser, LanguageParser)


def test_language_name():
    assert PythonParser().get_language_name() == "python"


def test_supported_extensions():
    assert PythonParser().get_supported_extensions() == [".py"]


def test_excluded_dirs():
    excluded = PythonParser().get_excluded_dirs()
    assert "__pycache__" in excluded
    assert "venv" in excluded


def test_node_type_definitions_not_empty():
    defs = PythonParser().get_node_type_definitions()
    assert len(defs) > 0
    names = {d.name for d in defs}
    assert "File" in names
    assert "Class" in names
    assert "Function" in names


def test_relationship_type_definitions_not_empty():
    defs = PythonParser().get_relationship_type_definitions()
    assert len(defs) > 0
    names = {d.name for d in defs}
    assert "CONTAINS" in names


def test_parse_file_sets_language():
    parser = PythonParser()
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("class Foo:\n    pass\n")
        f.flush()
        try:
            result = parser.parse_file(f.name)
            assert len(result.nodes) > 0
            for node in result.nodes:
                assert node.language == "python"
        finally:
            os.unlink(f.name)


def test_parse_files_sets_language():
    parser = PythonParser()
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        try:
            result = parser.parse_files([f.name])
            for node in result.nodes:
                assert node.language == "python"
        finally:
            os.unlink(f.name)


def test_create_cross_file_resolver():
    parser = PythonParser()
    resolver = parser.create_cross_file_resolver()
    assert resolver is not None
