"""Tests for JavaParser."""

from pathlib import Path

import pytest

from codeminer.parsing.java.parser import JavaParser
from codeminer.parsing.models import ASTResult

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "sample_project"


@pytest.fixture
def parser():
    return JavaParser()


@pytest.fixture
def parse_source(parser, tmp_path):
    """Helper: write Java source to a temp file and parse it."""

    def _parse(source: str, filename: str = "Test.java"):
        java_file = tmp_path / filename
        java_file.write_text(source)
        return parser.parse_file(str(java_file), str(tmp_path))

    return _parse


@pytest.fixture
def parse_fixture(parser):
    """Parse a single file from the sample_project fixtures."""

    def _parse(relative_path: str):
        file_path = FIXTURES_ROOT / relative_path
        return parser.parse_file(str(file_path), str(FIXTURES_ROOT))

    return _parse


class TestJavaParserMetadata:
    """Tests for parser metadata methods."""

    def test_language_name(self, parser):
        assert parser.get_language_name() == "java"

    def test_supported_extensions(self, parser):
        assert parser.get_supported_extensions() == [".java"]

    def test_excluded_dirs(self, parser):
        dirs = parser.get_excluded_dirs()
        assert "target" in dirs
        assert "build" in dirs
        assert ".gradle" in dirs
        assert ".idea" in dirs

    def test_node_type_definitions(self, parser):
        defs = parser.get_node_type_definitions()
        names = {d.name for d in defs}
        assert names == {
            "File",
            "Package",
            "Class",
            "Interface",
            "Enum",
            "Method",
            "Constructor",
            "Variable",
            "Import",
            "ExternalModule",
        }
        for d in defs:
            assert d.language == "java"

    def test_relationship_type_definitions(self, parser):
        defs = parser.get_relationship_type_definitions()
        names = {d.name for d in defs}
        assert names == {
            "CONTAINS",
            "EXTENDS",
            "IMPLEMENTS",
            "DEPENDS_ON",
            "IMPORTS",
        }
        for d in defs:
            assert d.language == "java"


class TestJavaParserFixtureNodeTypes:
    """Verify all Java-applicable CoreNodeType values are extracted from fixture files."""

    def test_class_fixture_nodes(self, parse_fixture):
        """Animal.java: File, Package, Class, Constructor, Method, Variable."""
        result = parse_fixture("com/example/model/Animal.java")
        types = {n.type for n in result.nodes}
        assert {
            "File",
            "Package",
            "Class",
            "Constructor",
            "Method",
            "Variable",
        } <= types

        class_node = next(n for n in result.nodes if n.type == "Class")
        assert class_node.name == "Animal"
        assert class_node.signature == "class Animal"

        ctor = next(n for n in result.nodes if n.type == "Constructor")
        assert ctor.name == "Animal"
        assert ctor.signature == "Animal(String name, int age)"

        fields = {n.name for n in result.nodes if n.type == "Variable"}
        assert fields == {"name", "age"}

        methods = {n.name for n in result.nodes if n.type == "Method"}
        assert methods == {"getName", "speak"}

    def test_interface_fixture(self, parse_fixture):
        """Named.java: interface with single method."""
        result = parse_fixture("com/example/service/Named.java")
        ifaces = [n for n in result.nodes if n.type == "Interface"]
        assert len(ifaces) == 1
        assert ifaces[0].name == "Named"
        # Interface method is also captured by method query
        methods = [n for n in result.nodes if n.type == "Method"]
        assert any(m.name == "getName" for m in methods)

    def test_interface_extending_interface(self, parse_fixture):
        """Walker.java: interface extends Named — base_classes is populated."""
        result = parse_fixture("com/example/service/Walker.java")
        iface = next(n for n in result.nodes if n.type == "Interface")
        assert iface.name == "Walker"
        assert iface.base_classes == ["Named"]

    def test_enum_fixture_full(self, parse_fixture):
        """Color.java: enum + constructor + method + field."""
        result = parse_fixture("com/example/model/Color.java")
        types = {n.type for n in result.nodes}
        assert "Enum" in types
        assert "Constructor" in types
        assert "Method" in types
        assert "Variable" in types

        enum_node = next(n for n in result.nodes if n.type == "Enum")
        assert enum_node.name == "Color"
        ctor = next(n for n in result.nodes if n.type == "Constructor")
        assert ctor.name == "Color"
        method = next(n for n in result.nodes if n.type == "Method")
        assert method.name == "getBrightness"
        field = next(n for n in result.nodes if n.type == "Variable")
        assert field.name == "brightness"

    def test_class_with_extends_and_implements(self, parse_fixture):
        """Dog.java: extends Animal + implements Walker — both in base_classes."""
        result = parse_fixture("com/example/model/Dog.java")
        class_node = next(
            n for n in result.nodes if n.type == "Class" and n.name == "Dog"
        )
        assert class_node.base_classes is not None
        assert "Animal" in class_node.base_classes
        assert "Walker" in class_node.base_classes

    def test_class_with_annotations(self, parse_fixture):
        """AnimalService.java has @Service, @Transactional annotations."""
        result = parse_fixture("com/example/service/AnimalService.java")
        class_node = next(n for n in result.nodes if n.type == "Class")
        assert class_node.decorators == ["Service", "Transactional"]

    def test_package_and_imports_from_fixture(self, parse_fixture):
        """AnimalService.java: package + multiple internal + external imports."""
        result = parse_fixture("com/example/service/AnimalService.java")
        pkg_nodes = [n for n in result.nodes if n.type == "Package"]
        assert len(pkg_nodes) == 1
        assert pkg_nodes[0].name == "com.example.service"
        assert pkg_nodes[0].module_path == "com.example.service"

        import_modules = {ri.module for ri in result.raw_imports}
        assert import_modules == {
            "java.util.ArrayList",
            "java.util.List",
            "com.example.model.Animal",
            "com.example.model.Dog",
            "com.example.model.Color",
        }

    def test_language_set_on_fixture_nodes(self, parse_fixture):
        result = parse_fixture("com/example/model/Animal.java")
        for node in result.nodes:
            assert node.language == "java"

    def test_raw_import_file_node_id_matches_fixture(self, parse_fixture):
        """raw_imports.source_file_node_id must match the File node id."""
        result = parse_fixture("com/example/service/AnimalService.java")
        file_node = next(n for n in result.nodes if n.type == "File")
        for ri in result.raw_imports:
            assert ri.source_file_node_id == file_node.id


class TestJavaParserContainsRelationships:
    """Tests for intra-file CONTAINS relationships using fixtures."""

    def test_file_contains_package_class(self, parse_fixture):
        result = parse_fixture("com/example/model/Animal.java")
        contains = [r for r in result.relationships if r.type == "CONTAINS"]
        file_node = next(n for n in result.nodes if n.type == "File")
        pkg = next(n for n in result.nodes if n.type == "Package")
        class_node = next(n for n in result.nodes if n.type == "Class")

        assert any(
            r.source_id == file_node.id and r.target_id == pkg.id for r in contains
        )
        assert any(
            r.source_id == file_node.id and r.target_id == class_node.id
            for r in contains
        )

    def test_class_contains_members(self, parse_fixture):
        """Class CONTAINS its Constructor, Method, Variable children."""
        result = parse_fixture("com/example/model/Animal.java")
        contains = [r for r in result.relationships if r.type == "CONTAINS"]
        class_node = next(n for n in result.nodes if n.type == "Class")

        child_ids = {r.target_id for r in contains if r.source_id == class_node.id}
        ctor = next(n for n in result.nodes if n.type == "Constructor")
        methods = [n for n in result.nodes if n.type == "Method"]
        fields = [n for n in result.nodes if n.type == "Variable"]

        assert ctor.id in child_ids
        for m in methods:
            assert m.id in child_ids
        for f in fields:
            assert f.id in child_ids

    def test_enum_contains_members(self, parse_fixture):
        """Color enum CONTAINS its Constructor, Method, Variable."""
        result = parse_fixture("com/example/model/Color.java")
        contains = [r for r in result.relationships if r.type == "CONTAINS"]
        enum_node = next(n for n in result.nodes if n.type == "Enum")

        child_ids = {r.target_id for r in contains if r.source_id == enum_node.id}
        ctor = next(n for n in result.nodes if n.type == "Constructor")
        method = next(n for n in result.nodes if n.type == "Method")
        field = next(n for n in result.nodes if n.type == "Variable")

        assert ctor.id in child_ids
        assert method.id in child_ids
        assert field.id in child_ids


class TestJavaParserEdgeCases:
    """Edge-case tests using inline sources (not worth a fixture file)."""

    def test_class_without_annotations_has_no_decorators(self, parse_source):
        result = parse_source("public class Plain { }")
        class_node = next(n for n in result.nodes if n.type == "Class")
        assert class_node.decorators is None

    def test_syntax_error_returns_parse_error(self, parse_source):
        """Malformed Java should still parse (tree-sitter is error-tolerant)."""
        result = parse_source("public class { }")
        assert isinstance(result, ASTResult)

    def test_wildcard_import_not_parsed(self, parse_source):
        """Wildcard imports (import java.util.*) are partially captured — the
        scoped_identifier query matches the package prefix but drops the
        asterisk wildcard, so the Import node name is 'java.util' rather than
        'java.util.*'."""
        result = parse_source("""
import java.util.*;
public class Foo { }
""")
        import_nodes = [n for n in result.nodes if n.type == "Import"]
        assert len(import_nodes) == 1
        assert import_nodes[0].name == "java.util"
        assert len(result.raw_imports) == 1
        assert result.raw_imports[0].module == "java.util"


class TestJavaParserNoDuplicateNodes:
    """Verify that no duplicated nodes are produced during parsing."""

    def test_no_duplicate_node_ids_single_file(self, parse_fixture):
        """All node IDs returned from a single-file parse are unique."""
        result = parse_fixture("com/example/model/Animal.java")
        ids = [n.id for n in result.nodes]
        assert len(ids) == len(set(ids)), f"Duplicate node IDs found: {ids}"

    def test_no_duplicate_nodes_by_identity_single_file(self, parse_fixture):
        """No two nodes in a single-file parse share (type, start_line).

        Guards against a tree-sitter query matching the same AST position twice.
        """
        result = parse_fixture("com/example/model/Animal.java")
        identities = [(n.type, n.start_line) for n in result.nodes]
        assert len(identities) == len(set(identities)), (
            f"Duplicate (type, start_line) pairs found: "
            f"{[x for x in identities if identities.count(x) > 1]}"
        )

    def test_no_duplicate_node_ids_multi_file(self, parser):
        """All node IDs returned by parse_files over the sample project are unique."""
        java_files = sorted(str(p) for p in FIXTURES_ROOT.rglob("*.java"))
        result = parser.parse_files(java_files, str(FIXTURES_ROOT))
        ids = [n.id for n in result.nodes]
        assert len(ids) == len(set(ids)), (
            f"Duplicate node IDs found across {len(java_files)} files"
        )

    def test_no_duplicate_nodes_by_identity_multi_file(self, parser):
        """No two nodes across all parsed files share (source_file, type, start_line)."""
        java_files = sorted(str(p) for p in FIXTURES_ROOT.rglob("*.java"))
        result = parser.parse_files(java_files, str(FIXTURES_ROOT))
        identities = [(n.source_file, n.type, n.start_line) for n in result.nodes]
        duplicates = [x for x in identities if identities.count(x) > 1]
        assert not duplicates, f"Duplicate (source_file, type, start_line) found: {duplicates}"

    def test_package_nodes_are_unique_by_module_path_multi_file(self, parser):
        """Sample project should keep only the first Package node per module_path."""
        java_files = sorted(str(p) for p in FIXTURES_ROOT.rglob("*.java"))
        result = parser.parse_files(java_files, str(FIXTURES_ROOT))

        package_nodes = [n for n in result.nodes if n.type == "Package"]
        module_paths = [n.module_path for n in package_nodes]

        assert len(module_paths) == len(set(module_paths)), (
            f"Duplicate Package module_paths found: {module_paths}"
        )
        assert set(module_paths) == {
            "com.example.app",
            "com.example.model",
            "com.example.service",
        }

    def test_deduped_package_nodes_keep_relationship_targets_valid(self, parser):
        """Package deduplication should not leave any relationship pointing at removed ids."""
        java_files = sorted(str(p) for p in FIXTURES_ROOT.rglob("*.java"))
        result = parser.parse_files(java_files, str(FIXTURES_ROOT))

        node_ids = {n.id for n in result.nodes}
        dangling_relationships = [
            (r.type, r.source_id, r.target_id)
            for r in result.relationships
            if r.source_id not in node_ids or r.target_id not in node_ids
        ]

        assert not dangling_relationships, (
            f"Relationships reference removed node ids: {dangling_relationships}"
        )

    def test_no_duplicate_package_nodes_after_cross_file_resolve(self, parser):
        """Regression: cross-file resolver must not re-introduce Package nodes already
        present in result.nodes.  Simulates what AnalysisOrchestrator does:
        parse_files → resolver.resolve() → result.nodes.extend(new_nodes).
        """
        from codeminer.parsing.java.cross_file_resolver import JavaCrossFileResolver

        java_files = sorted(str(p) for p in FIXTURES_ROOT.rglob("*.java"))
        result = parser.parse_files(java_files, str(FIXTURES_ROOT))

        resolver = JavaCrossFileResolver()
        new_rels, new_nodes = resolver.resolve(result)
        result.nodes.extend(new_nodes)
        result.relationships.extend(new_rels)

        package_nodes = [n for n in result.nodes if n.type == "Package"]
        module_paths = [n.module_path for n in package_nodes]
        assert len(module_paths) == len(set(module_paths)), (
            f"Duplicate Package nodes after resolve: {module_paths}"
        )

    def test_parsing_same_file_twice_gives_independent_nodes(self, parser):
        """Parsing the same file twice returns two fully disjoint node-ID sets.

        Verifies that no per-file state leaks between consecutive parse_file calls.
        """
        file_path = str(FIXTURES_ROOT / "com/example/model/Animal.java")
        result_a = parser.parse_file(file_path, str(FIXTURES_ROOT))
        result_b = parser.parse_file(file_path, str(FIXTURES_ROOT))
        ids_a = {n.id for n in result_a.nodes}
        ids_b = {n.id for n in result_b.nodes}
        shared = ids_a & ids_b
        assert not shared, f"Node IDs shared between two independent parses: {shared}"


PACKAGE_ONLY_ROOT = Path(__file__).parent / "fixtures" / "package_only"


@pytest.fixture
def package_only_fixture_root():
    return PACKAGE_ONLY_ROOT


@pytest.fixture
def parse_package_only(parser, package_only_fixture_root):
    """Parse a single file from the package_only fixtures."""

    def _parse(relative_path: str):
        file_path = package_only_fixture_root / relative_path
        return parser.parse_file(str(file_path), str(package_only_fixture_root))

    return _parse


class TestJavaParserPackageOnly:
    """Tests for files that declare only a package (no class or interface)."""

    def test_package_only_file_has_no_class_or_interface(self, parse_package_only):
        result = parse_package_only("com/example/empty/PackageOnly.java")
        node_types = {n.type for n in result.nodes}
        assert "Package" in node_types
        pkg_node = next(n for n in result.nodes if n.type == "Package")
        assert pkg_node.name == "com.example.empty"
        assert "Class" not in node_types
        assert "Interface" not in node_types

    def test_package_only_file_has_no_raw_imports(self, parse_package_only):
        result = parse_package_only("com/example/empty/PackageOnly.java")
        assert result.raw_imports == []

    def test_package_only_file_contains_only_file_and_package_nodes(
        self, parse_package_only
    ):
        result = parse_package_only("com/example/empty/PackageOnly.java")
        node_types = {n.type for n in result.nodes}
        assert node_types <= {"File", "Package"}
