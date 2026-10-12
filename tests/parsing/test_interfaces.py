import pytest
from codeminer.parsing.interfaces import LanguageParser, CrossFileResolverBase
from codeminer.parsing.models import ASTResult
from codeminer.parsing.types import NodeTypeDefinition, RelationshipTypeDefinition


class MockParser(LanguageParser):
    def get_language_name(self) -> str:
        return "mock"

    def get_supported_extensions(self) -> list[str]:
        return [".mock"]

    def get_node_type_definitions(self) -> list[NodeTypeDefinition]:
        return []

    def get_relationship_type_definitions(self) -> list[RelationshipTypeDefinition]:
        return []

    def get_excluded_dirs(self) -> set[str]:
        return {"mock_cache"}

    def parse_file(self, file_path, project_root=None) -> ASTResult:
        return ASTResult()

    def parse_files(self, file_paths, project_root=None) -> ASTResult:
        return ASTResult()

    def create_cross_file_resolver(self):
        return None


class MockResolver(CrossFileResolverBase):
    def resolve(self, ast_result, config=None):
        return [], []


def test_language_parser_can_be_subclassed():
    parser = MockParser()
    assert parser.get_language_name() == "mock"
    assert parser.get_supported_extensions() == [".mock"]
    assert "mock_cache" in parser.get_excluded_dirs()


def test_cross_file_resolver_can_be_subclassed():
    resolver = MockResolver()
    rels, nodes = resolver.resolve(ASTResult())
    assert rels == []
    assert nodes == []


def test_language_parser_is_abstract():
    with pytest.raises(TypeError):
        LanguageParser()


def test_cross_file_resolver_is_abstract():
    with pytest.raises(TypeError):
        CrossFileResolverBase()
