import pytest
from codeminer.parsing.registry import ParserRegistry
from codeminer.parsing.interfaces import LanguageParser
from codeminer.parsing.models import ASTResult
from codeminer.parsing.types import NodeTypeDefinition, RelationshipTypeDefinition


class StubParser(LanguageParser):
    def __init__(self, name, extensions, excluded_dirs=None):
        self._name = name
        self._extensions = extensions
        self._excluded = excluded_dirs or set()

    def get_language_name(self):
        return self._name

    def get_supported_extensions(self):
        return self._extensions

    def get_node_type_definitions(self):
        return [NodeTypeDefinition(name="File", language=self._name, category="structure", description="A file")]

    def get_relationship_type_definitions(self):
        return [RelationshipTypeDefinition(name="CONTAINS", language=self._name, category="structural", description="Contains")]

    def get_excluded_dirs(self):
        return self._excluded

    def parse_file(self, file_path, project_root=None):
        return ASTResult()

    def parse_files(self, file_paths, project_root=None):
        return ASTResult()

    def create_cross_file_resolver(self):
        return None


def test_register_and_get_by_language():
    reg = ParserRegistry()
    parser = StubParser("python", [".py"])
    reg.register(parser)
    assert reg.get_parser_for_language("python") is parser


def test_get_parser_for_extension():
    reg = ParserRegistry()
    parser = StubParser("python", [".py"])
    reg.register(parser)
    assert reg.get_parser_for_extension(".py") is parser


def test_get_parser_for_unknown_extension():
    reg = ParserRegistry()
    assert reg.get_parser_for_extension(".xyz") is None


def test_get_parser_for_unknown_language():
    reg = ParserRegistry()
    assert reg.get_parser_for_language("rust") is None


def test_get_supported_languages():
    reg = ParserRegistry()
    reg.register(StubParser("python", [".py"]))
    reg.register(StubParser("java", [".java"]))
    assert sorted(reg.get_supported_languages()) == ["java", "python"]


def test_get_all_node_type_definitions():
    reg = ParserRegistry()
    reg.register(StubParser("python", [".py"]))
    reg.register(StubParser("java", [".java"]))
    defs = reg.get_all_node_type_definitions()
    assert len(defs) == 2
    assert {d.language for d in defs} == {"python", "java"}


def test_get_all_relationship_type_definitions():
    reg = ParserRegistry()
    reg.register(StubParser("python", [".py"]))
    defs = reg.get_all_relationship_type_definitions()
    assert len(defs) == 1


def test_get_definitions_for_language():
    reg = ParserRegistry()
    reg.register(StubParser("python", [".py"]))
    defs = reg.get_definitions_for_language("python")
    assert "node_types" in defs
    assert "relationship_types" in defs


def test_get_definitions_for_unknown_language():
    reg = ParserRegistry()
    defs = reg.get_definitions_for_language("rust")
    assert defs["node_types"] == []
    assert defs["relationship_types"] == []


def test_duplicate_language_raises():
    reg = ParserRegistry()
    reg.register(StubParser("python", [".py"]))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(StubParser("python", [".py"]))


def test_duplicate_extension_raises():
    reg = ParserRegistry()
    reg.register(StubParser("python", [".py"]))
    with pytest.raises(ValueError, match="already claimed"):
        reg.register(StubParser("cython", [".py", ".pyx"]))
