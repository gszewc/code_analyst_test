"""Tests for JavaCrossFileResolver."""

import uuid
from pathlib import Path

import pytest

from codeminer.parsing.java.cross_file_resolver import JavaCrossFileResolver
from codeminer.parsing.java.parser import JavaParser
from codeminer.parsing.models import ASTNode, ASTResult, RawImport

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "sample_project"


def _node(type: str, name: str, source_file: str, **kwargs) -> ASTNode:
    """Create a test ASTNode with sensible defaults."""
    return ASTNode(
        id=str(uuid.uuid4()),
        type=type,
        name=name,
        source_file=source_file,
        start_line=1,
        end_line=10,
        language="java",
        **kwargs,
    )


def _raw_import(source_file: str, source_file_node_id: str, module: str) -> RawImport:
    """Create a test RawImport.

    mirrors what JavaParser produces: names=[simple_class_name] derived from the last
    component of the fully-qualified module name.
    """
    parts = module.rsplit(".", 1)
    simple_name = parts[-1] if len(parts) > 1 else module
    return RawImport(
        source_file=source_file,
        source_file_node_id=source_file_node_id,
        module=module,
        names=[simple_name],
        level=0,
    )


class TestJavaCrossFileResolver:
    """Tests for JavaCrossFileResolver."""

    def test_resolves_internal_import(self):
        """Import of a class in the same project emits IMPORTS + DEPENDS_ON."""
        file_a = _node("File", "UserService.java", "src/UserService.java")
        class_a = _node("Class", "UserService", "src/UserService.java")
        pkg_a = _node(
            "Package", "com.example", "src/UserService.java", module_path="com.example"
        )

        file_b = _node("File", "App.java", "src/App.java")
        class_b = _node("Class", "App", "src/App.java")

        raw_import = _raw_import("src/App.java", file_b.id, "com.example.UserService")

        ast_result = ASTResult(
            nodes=[file_a, class_a, pkg_a, file_b, class_b],
            raw_imports=[raw_import],
        )

        resolver = JavaCrossFileResolver()
        new_rels, new_nodes = resolver.resolve(ast_result)

        rel_types = {r.type for r in new_rels}
        assert "IMPORTS" in rel_types
        assert "DEPENDS_ON" in rel_types

        # IMPORTS should target the class node
        imports_rel = next(r for r in new_rels if r.type == "IMPORTS")
        assert imports_rel.source_id == file_b.id
        assert imports_rel.target_id == class_a.id

    def test_resolves_external_import(self):
        """Import of unknown class creates ExternalModule + IMPORTS."""
        file_a = _node("File", "App.java", "src/App.java")

        raw_import = _raw_import("src/App.java", file_a.id, "java.util.List")

        ast_result = ASTResult(
            nodes=[file_a],
            raw_imports=[raw_import],
        )

        resolver = JavaCrossFileResolver()
        new_rels, new_nodes = resolver.resolve(ast_result)

        assert len(new_nodes) == 1
        assert new_nodes[0].type == "ExternalModule"
        assert new_nodes[0].name == "java.util.List"

        imports_rel = next(r for r in new_rels if r.type == "IMPORTS")
        assert imports_rel.target_id == new_nodes[0].id

    def test_deduplicates_depends_on(self):
        """Multiple imports from same source → same target file = one DEPENDS_ON."""
        file_a = _node("File", "Models.java", "src/Models.java")
        class_user = _node("Class", "User", "src/Models.java")
        class_role = _node("Class", "Role", "src/Models.java")
        pkg_a = _node(
            "Package", "com.example", "src/Models.java", module_path="com.example"
        )

        file_b = _node("File", "App.java", "src/App.java")

        raw_imports = [
            _raw_import("src/App.java", file_b.id, "com.example.User"),
            _raw_import("src/App.java", file_b.id, "com.example.Role"),
        ]

        ast_result = ASTResult(
            nodes=[file_a, class_user, class_role, pkg_a, file_b],
            raw_imports=raw_imports,
        )

        resolver = JavaCrossFileResolver()
        new_rels, _ = resolver.resolve(ast_result)

        depends_on = [r for r in new_rels if r.type == "DEPENDS_ON"]
        # Both imports point to the same target file → only one DEPENDS_ON
        assert len(depends_on) == 1

    def test_resolves_extends(self):
        """Class extending another in same project emits EXTENDS."""
        file_a = _node("File", "Animal.java", "src/Animal.java")
        class_a = _node("Class", "Animal", "src/Animal.java")

        file_b = _node("File", "Dog.java", "src/Dog.java")
        class_b = _node("Class", "Dog", "src/Dog.java", base_classes=["Animal"])

        ast_result = ASTResult(nodes=[file_a, class_a, file_b, class_b])

        resolver = JavaCrossFileResolver()
        new_rels, _ = resolver.resolve(ast_result)

        extends_rels = [r for r in new_rels if r.type == "EXTENDS"]
        assert len(extends_rels) == 1
        assert extends_rels[0].source_id == class_b.id
        assert extends_rels[0].target_id == class_a.id

    def test_resolves_implements(self):
        """Class implementing interface in same project emits IMPLEMENTS."""
        file_a = _node("File", "Greeter.java", "src/Greeter.java")
        iface = _node("Interface", "Greeter", "src/Greeter.java")

        file_b = _node("File", "HelloGreeter.java", "src/HelloGreeter.java")
        class_b = _node(
            "Class", "HelloGreeter", "src/HelloGreeter.java", base_classes=["Greeter"]
        )

        ast_result = ASTResult(nodes=[file_a, iface, file_b, class_b])

        resolver = JavaCrossFileResolver()
        new_rels, _ = resolver.resolve(ast_result)

        implements_rels = [r for r in new_rels if r.type == "IMPLEMENTS"]
        assert len(implements_rels) == 1
        assert implements_rels[0].source_id == class_b.id
        assert implements_rels[0].target_id == iface.id

    def test_skips_unknown_base_class(self):
        """External base class → no node synthesised, no error."""
        file_a = _node("File", "Foo.java", "src/Foo.java")
        class_a = _node("Class", "Foo", "src/Foo.java", base_classes=["ExternalBase"])

        ast_result = ASTResult(nodes=[file_a, class_a])

        resolver = JavaCrossFileResolver()
        new_rels, new_nodes = resolver.resolve(ast_result)

        extends_rels = [r for r in new_rels if r.type == "EXTENDS"]
        assert len(extends_rels) == 0
        # No ExternalModule nodes synthesised for inheritance
        assert all(n.type != "ExternalModule" for n in new_nodes)


@pytest.fixture
def sample_project_result():
    """Parse all .java files under fixtures/sample_project and merge results."""
    parser = JavaParser()
    java_files = sorted(str(p) for p in FIXTURES_ROOT.rglob("*.java"))
    return parser.parse_files(java_files, str(FIXTURES_ROOT))


@pytest.fixture
def sample_project_resolved(sample_project_result):
    """Parse the sample project and run the cross-file resolver.

    Returns (merged_ast_result, new_relationships, new_nodes). The merged
    result contains the original AST plus the resolver's new nodes and
    relationships, so callers can look up targets by id directly.
    """
    resolver = JavaCrossFileResolver()
    new_rels, new_nodes = resolver.resolve(sample_project_result)

    merged = ASTResult(
        nodes=list(sample_project_result.nodes) + new_nodes,
        relationships=list(sample_project_result.relationships) + new_rels,
        raw_imports=sample_project_result.raw_imports,
    )
    return merged, new_rels, new_nodes


def _find(nodes, **criteria):
    """Find the first node matching all given attribute criteria."""
    for n in nodes:
        if all(getattr(n, k) == v for k, v in criteria.items()):
            return n
    return None


class TestJavaCrossFileResolverFixtures:
    """End-to-end cross-file resolution against the sample_project fixture."""

    def test_all_fixture_files_parsed_without_errors(self, sample_project_result):
        assert sample_project_result.errors == []
        # 7 .java files in the fixture
        file_nodes = [n for n in sample_project_result.nodes if n.type == "File"]
        assert len(file_nodes) == 7

    def test_internal_imports_become_imports_relationships(
        self, sample_project_resolved
    ):
        """AnimalService.java imports Animal, Dog, Color — all internal."""
        merged, new_rels, _ = sample_project_resolved
        service_file = _find(
            merged.nodes,
            type="File",
            source_file="com/example/service/AnimalService.java",
        )
        assert service_file is not None

        animal = _find(merged.nodes, type="Class", name="Animal")
        dog = _find(merged.nodes, type="Class", name="Dog")
        color = _find(merged.nodes, type="Enum", name="Color")

        imports_from_service = {
            r.target_id
            for r in new_rels
            if r.type == "IMPORTS" and r.source_id == service_file.id
        }
        assert animal.id in imports_from_service
        assert dog.id in imports_from_service
        assert color.id in imports_from_service

    def test_external_imports_create_external_module_nodes(
        self, sample_project_resolved
    ):
        """java.util.ArrayList and java.util.List are unknown → ExternalModule."""
        _, new_rels, new_nodes = sample_project_resolved
        ext_names = {n.name for n in new_nodes if n.type == "ExternalModule"}
        assert "java.util.ArrayList" in ext_names
        assert "java.util.List" in ext_names

        # Each ExternalModule has at least one IMPORTS relationship pointing to it
        ext_ids = {n.id for n in new_nodes if n.type == "ExternalModule"}
        import_targets = {r.target_id for r in new_rels if r.type == "IMPORTS"}
        assert ext_ids & import_targets == ext_ids

    def test_depends_on_deduplicated_between_files(self, sample_project_resolved):
        """AnimalService imports Animal + Dog + Color (all from com/example/model);
        Dog.java imports Walker (single file); App.java imports AnimalService + Dog.

        DEPENDS_ON is file→file deduplicated, so AnimalService→(Animal.java,
        Dog.java, Color.java) is 3 edges not 3+."""
        merged, new_rels, _ = sample_project_resolved
        service_file = _find(
            merged.nodes,
            type="File",
            source_file="com/example/service/AnimalService.java",
        )
        depends_on = [
            r
            for r in new_rels
            if r.type == "DEPENDS_ON" and r.source_id == service_file.id
        ]
        # Dedup check: no duplicate (source, target) pairs
        pairs = {(r.source_id, r.target_id) for r in depends_on}
        assert len(pairs) == len(depends_on)

        target_files = {
            _find(merged.nodes, id=r.target_id).source_file for r in depends_on
        }
        assert target_files == {
            "com/example/model/Animal.java",
            "com/example/model/Dog.java",
            "com/example/model/Color.java",
        }

    def test_class_extends_class_cross_file(self, sample_project_resolved):
        """Dog extends Animal (different files) → EXTENDS relationship."""
        merged, new_rels, _ = sample_project_resolved
        dog = _find(merged.nodes, type="Class", name="Dog")
        animal = _find(merged.nodes, type="Class", name="Animal")

        extends = [
            r
            for r in new_rels
            if r.type == "EXTENDS"
            and r.source_id == dog.id
            and r.target_id == animal.id
        ]
        assert len(extends) == 1

    def test_interface_extends_interface_cross_file(self, sample_project_resolved):
        """Walker extends Named (different files) → EXTENDS between interfaces."""
        merged, new_rels, _ = sample_project_resolved
        walker = _find(merged.nodes, type="Interface", name="Walker")
        named = _find(merged.nodes, type="Interface", name="Named")

        extends = [
            r
            for r in new_rels
            if r.type == "EXTENDS"
            and r.source_id == walker.id
            and r.target_id == named.id
        ]
        assert len(extends) == 1

    def test_class_implements_interface_cross_file(self, sample_project_resolved):
        """Dog implements Walker (different files) → IMPLEMENTS relationship."""
        merged, new_rels, _ = sample_project_resolved
        dog = _find(merged.nodes, type="Class", name="Dog")
        walker = _find(merged.nodes, type="Interface", name="Walker")

        impls = [
            r
            for r in new_rels
            if r.type == "IMPLEMENTS"
            and r.source_id == dog.id
            and r.target_id == walker.id
        ]
        assert len(impls) == 1

    def test_all_supported_node_types_present_in_fixtures(
        self, sample_project_result, sample_project_resolved
    ):
        """Verify every node type declared in get_node_type_definitions() is
        represented in the end-to-end fixture parse."""
        _, _, new_nodes = sample_project_resolved
        all_types = {n.type for n in sample_project_result.nodes}
        all_types |= {n.type for n in new_nodes}

        parser = JavaParser()
        declared = {d.name for d in parser.get_node_type_definitions()}
        assert declared <= all_types, f"missing types: {declared - all_types}"

    def test_all_supported_relationship_types_present_in_fixtures(
        self, sample_project_result, sample_project_resolved
    ):
        """Verify every relationship type declared in
        get_relationship_type_definitions() is emitted end-to-end."""
        _, new_rels, _ = sample_project_resolved
        all_rel_types = {r.type for r in sample_project_result.relationships}
        all_rel_types |= {r.type for r in new_rels}

        parser = JavaParser()
        declared = {d.name for d in parser.get_relationship_type_definitions()}
        assert (
            declared <= all_rel_types
        ), f"missing relationship types: {declared - all_rel_types}"


# ---------------------------------------------------------------------------
# T003: Package-only fixture + shared helpers
# ---------------------------------------------------------------------------

PACKAGE_ONLY_ROOT = Path(__file__).parent / "fixtures" / "package_only"


@pytest.fixture
def package_only_result():
    """Parse all .java files under fixtures/package_only and merge results."""
    parser = JavaParser()
    java_files = sorted(str(p) for p in PACKAGE_ONLY_ROOT.rglob("*.java"))
    return parser.parse_files(java_files, str(PACKAGE_ONLY_ROOT))


@pytest.fixture
def package_only_resolved(package_only_result):
    """Run the cross-file resolver over the package_only fixture.

    Returns (merged_ast_result, new_relationships, new_nodes).
    """
    resolver = JavaCrossFileResolver()
    new_rels, new_nodes = resolver.resolve(package_only_result)

    merged = ASTResult(
        nodes=list(package_only_result.nodes) + new_nodes,
        relationships=list(package_only_result.relationships) + new_rels,
        raw_imports=package_only_result.raw_imports,
    )
    return merged, new_rels, new_nodes


def _contains_rels(rels, pkg_node, type_node):
    """Return all CONTAINS relationships from pkg_node.id to type_node.id."""
    return [
        r
        for r in rels
        if r.type == "CONTAINS"
        and r.source_id == pkg_node.id
        and r.target_id == type_node.id
    ]


# ---------------------------------------------------------------------------
# T005: [US1] Package→CONTAINS→Class/Interface — failing until implemented
# ---------------------------------------------------------------------------


class TestJavaPackageContainmentUS1:
    """Package containment resolver emits CONTAINS edges to Class/Interface nodes."""

    def test_package_contains_class_unit(self):
        """Package node + Class in same file → one CONTAINS edge in new_rels."""
        file_node = _node("File", "Foo.java", "src/Foo.java")
        pkg = _node("Package", "com.example", "src/Foo.java", module_path="com.example")
        cls = _node("Class", "Foo", "src/Foo.java")

        ast_result = ASTResult(nodes=[file_node, pkg, cls])
        new_rels, _ = JavaCrossFileResolver().resolve(ast_result)

        contains = _contains_rels(new_rels, pkg, cls)
        assert len(contains) == 1

    def test_package_contains_interface_unit(self):
        """Package node + Interface in same file → one CONTAINS edge in new_rels."""
        file_node = _node("File", "IFoo.java", "src/IFoo.java")
        pkg = _node(
            "Package", "com.example", "src/IFoo.java", module_path="com.example"
        )
        iface = _node("Interface", "IFoo", "src/IFoo.java")

        ast_result = ASTResult(nodes=[file_node, pkg, iface])
        new_rels, _ = JavaCrossFileResolver().resolve(ast_result)

        contains = _contains_rels(new_rels, pkg, iface)
        assert len(contains) == 1

    def test_two_packages_contain_respective_types(self):
        """Two packages each with a class → each package contains only its own class."""
        pkg_a = _node(
            "Package", "com.example.a", "src/A.java", module_path="com.example.a"
        )
        cls_a = _node("Class", "A", "src/A.java")

        pkg_b = _node(
            "Package", "com.example.b", "src/B.java", module_path="com.example.b"
        )
        cls_b = _node("Class", "B", "src/B.java")

        ast_result = ASTResult(nodes=[pkg_a, cls_a, pkg_b, cls_b])
        new_rels, _ = JavaCrossFileResolver().resolve(ast_result)

        contains = [r for r in new_rels if r.type == "CONTAINS"]
        assert len(contains) == 2

        sources = {r.source_id for r in contains}
        assert pkg_a.id in sources
        assert pkg_b.id in sources

        targets = {r.target_id for r in contains}
        assert cls_a.id in targets
        assert cls_b.id in targets

        # pkg_a must not contain cls_b and vice-versa
        assert not _contains_rels(new_rels, pkg_a, cls_b)
        assert not _contains_rels(new_rels, pkg_b, cls_a)

    def test_sample_project_packages_contain_classes(self, sample_project_resolved):
        """com.example.model package contains Animal and Dog (Class nodes)."""
        merged, new_rels, _ = sample_project_resolved

        model_pkg = _find(merged.nodes, type="Package", name="com.example.model")
        assert model_pkg is not None

        animal = _find(merged.nodes, type="Class", name="Animal")
        dog = _find(merged.nodes, type="Class", name="Dog")
        assert animal is not None
        assert dog is not None

        assert len(_contains_rels(new_rels, model_pkg, animal)) == 1
        assert len(_contains_rels(new_rels, model_pkg, dog)) == 1

    def test_sample_project_packages_contain_interfaces(self, sample_project_resolved):
        """com.example.service package contains Named and Walker (Interface nodes)."""
        merged, new_rels, _ = sample_project_resolved

        service_pkg = _find(merged.nodes, type="Package", name="com.example.service")
        assert service_pkg is not None

        named = _find(merged.nodes, type="Interface", name="Named")
        walker = _find(merged.nodes, type="Interface", name="Walker")
        assert named is not None
        assert walker is not None

        assert len(_contains_rels(new_rels, service_pkg, named)) == 1
        assert len(_contains_rels(new_rels, service_pkg, walker)) == 1


# ---------------------------------------------------------------------------
# T011: [US2] Artifact exclusion — failing until implemented
# ---------------------------------------------------------------------------


class TestJavaPackageContainmentUS2:
    """Package containment excludes Enums, nested Packages, and empty packages."""

    def test_package_only_file_emits_no_containment(self, package_only_resolved):
        """PackageOnly.java declares only a package; resolver should emit no CONTAINS."""
        merged, new_rels, _ = package_only_resolved

        pkg = _find(merged.nodes, type="Package", name="com.example.empty")
        assert pkg is not None, "Package node for com.example.empty not found"

        contains_from_pkg = [
            r for r in new_rels if r.type == "CONTAINS" and r.source_id == pkg.id
        ]
        assert contains_from_pkg == []

    def test_package_node_not_containment_target(self, sample_project_resolved):
        """No CONTAINS relationship should have a Package node as its target."""
        merged, new_rels, _ = sample_project_resolved

        pkg_ids = {n.id for n in merged.nodes if n.type == "Package"}
        contains_targeting_pkg = [
            r for r in new_rels if r.type == "CONTAINS" and r.target_id in pkg_ids
        ]
        assert contains_targeting_pkg == []

    def test_enum_not_package_containment_target(self, sample_project_resolved):
        """No CONTAINS relationship should have an Enum node as its target."""
        merged, new_rels, _ = sample_project_resolved

        enum_ids = {n.id for n in merged.nodes if n.type == "Enum"}
        contains_targeting_enum = [
            r for r in new_rels if r.type == "CONTAINS" and r.target_id in enum_ids
        ]
        assert contains_targeting_enum == []


# ---------------------------------------------------------------------------
# T014: [US3] Duplicate suppression — failing until implemented
# ---------------------------------------------------------------------------


class TestJavaPackageContainmentUS3:
    """Package containment resolver suppresses duplicate CONTAINS edges."""

    def test_no_duplicate_contains_edges_unit(self):
        """Two files in same package with different classes → exactly 2 CONTAINS edges."""
        # file_a.java
        pkg_a = _node(
            "Package", "com.example", "src/Foo.java", module_path="com.example"
        )
        cls_foo = _node("Class", "Foo", "src/Foo.java")

        # file_b.java — same package name, different file
        pkg_b = _node(
            "Package", "com.example", "src/Bar.java", module_path="com.example"
        )
        cls_bar = _node("Class", "Bar", "src/Bar.java")

        ast_result = ASTResult(nodes=[pkg_a, cls_foo, pkg_b, cls_bar])
        new_rels, _ = JavaCrossFileResolver().resolve(ast_result)

        contains = [r for r in new_rels if r.type == "CONTAINS"]
        # One CONTAINS per class, no cross-package duplicates
        assert len(contains) == 2

        target_ids = {r.target_id for r in contains}
        assert cls_foo.id in target_ids
        assert cls_bar.id in target_ids

    def test_no_duplicate_contains_for_same_type(self):
        """Same (package_name, class_name) pair declared in two Package nodes → exactly ONE CONTAINS edge."""
        # Both Package nodes claim the same package + the same Class is in the same file
        pkg_x = _node(
            "Package", "com.example", "src/Thing.java", module_path="com.example"
        )
        pkg_y = _node(
            "Package", "com.example", "src/Thing.java", module_path="com.example"
        )
        cls = _node("Class", "Thing", "src/Thing.java")

        ast_result = ASTResult(nodes=[pkg_x, pkg_y, cls])
        new_rels, _ = JavaCrossFileResolver().resolve(ast_result)

        contains = [
            r for r in new_rels if r.type == "CONTAINS" and r.target_id == cls.id
        ]
        assert len(contains) == 1


# ---------------------------------------------------------------------------
# T015: [US3] Regression — existing resolver behaviour preserved
# ---------------------------------------------------------------------------


class TestJavaPackageContainmentRegressionUS3:
    """Existing cross-file relationships are not broken when containment is added."""

    def test_imports_relationships_still_present(self, sample_project_resolved):
        """IMPORTS relationships must still be emitted after containment is added."""
        _, new_rels, _ = sample_project_resolved
        assert any(r.type == "IMPORTS" for r in new_rels)

    def test_depends_on_relationships_still_present(self, sample_project_resolved):
        """DEPENDS_ON relationships must still be emitted after containment is added."""
        _, new_rels, _ = sample_project_resolved
        assert any(r.type == "DEPENDS_ON" for r in new_rels)

    def test_extends_relationships_still_present(self, sample_project_resolved):
        """EXTENDS relationships must still be emitted after containment is added."""
        _, new_rels, _ = sample_project_resolved
        assert any(r.type == "EXTENDS" for r in new_rels)

    def test_implements_relationships_still_present(self, sample_project_resolved):
        """IMPLEMENTS relationships must still be emitted after containment is added."""
        _, new_rels, _ = sample_project_resolved
        assert any(r.type == "IMPLEMENTS" for r in new_rels)

    def test_external_module_nodes_still_created(self, sample_project_resolved):
        """ExternalModule nodes must still be synthesised for external imports."""
        _, _, new_nodes = sample_project_resolved
        assert any(n.type == "ExternalModule" for n in new_nodes)


# ---------------------------------------------------------------------------
# T009: Fixture-wide containment verification
# ---------------------------------------------------------------------------


class TestJavaPackageContainmentFixtureVerification:
    """Verify containment edges against every packaged type in the sample project."""

    def test_all_packaged_classes_have_containment_edge(self, sample_project_resolved):
        """For every Class node with a module_path, a CONTAINS edge from the correct
        Package node must exist in new_rels."""
        merged, new_rels, _ = sample_project_resolved

        # Build source_file → package_name from Package nodes in the parsed result
        file_to_pkg: dict[str, str] = {
            n.source_file: n.module_path
            for n in merged.nodes
            if n.type == "Package" and n.source_file and n.module_path
        }
        # canonical Package: first occurrence per module_path in merged.nodes
        pkg_node_index: dict[str, ASTNode] = {}
        for n in merged.nodes:
            if (
                n.type == "Package"
                and n.module_path
                and n.module_path not in pkg_node_index
            ):
                pkg_node_index[n.module_path] = n

        contains_set = {
            (r.source_id, r.target_id) for r in new_rels if r.type == "CONTAINS"
        }

        for node in merged.nodes:
            if node.type != "Class" or not node.source_file:
                continue
            pkg_name = file_to_pkg.get(node.source_file)
            if not pkg_name:
                continue
            pkg_node = pkg_node_index.get(pkg_name)
            assert (
                pkg_node is not None
            ), f"No Package node found for module_path {pkg_name!r}"
            assert (
                pkg_node.id,
                node.id,
            ) in contains_set, (
                f"Missing CONTAINS edge: Package '{pkg_name}' → Class '{node.name}'"
            )

    def test_all_packaged_interfaces_have_containment_edge(
        self, sample_project_resolved
    ):
        """For every Interface node with a module_path, a CONTAINS edge from the
        correct Package node must exist in new_rels."""
        merged, new_rels, _ = sample_project_resolved

        file_to_pkg: dict[str, str] = {
            n.source_file: n.module_path
            for n in merged.nodes
            if n.type == "Package" and n.source_file and n.module_path
        }
        pkg_node_index: dict[str, ASTNode] = {}
        for n in merged.nodes:
            if (
                n.type == "Package"
                and n.module_path
                and n.module_path not in pkg_node_index
            ):
                pkg_node_index[n.module_path] = n

        contains_set = {
            (r.source_id, r.target_id) for r in new_rels if r.type == "CONTAINS"
        }

        for node in merged.nodes:
            if node.type != "Interface" or not node.source_file:
                continue
            pkg_name = file_to_pkg.get(node.source_file)
            if not pkg_name:
                continue
            pkg_node = pkg_node_index.get(pkg_name)
            assert (
                pkg_node is not None
            ), f"No Package node found for module_path {pkg_name!r}"
            assert (
                pkg_node.id,
                node.id,
            ) in contains_set, (
                f"Missing CONTAINS edge: Package '{pkg_name}' → Interface '{node.name}'"
            )

    def test_containment_count_matches_expected(self, sample_project_resolved):
        """Total CONTAINS edges from Package nodes equals the number of
        Class + Interface nodes that belong to a package in the sample project.

        Sample project contains:
          com.example.app:     App (Class)                   = 1
          com.example.model:   Animal (Class), Dog (Class)   = 2
          com.example.service: AnimalService (Class),
                               Named (Interface),
                               Walker (Interface)             = 3
        Total = 6
        """
        merged, new_rels, _ = sample_project_resolved

        pkg_ids = {n.id for n in merged.nodes if n.type == "Package"}
        contains_from_pkg = [
            r for r in new_rels if r.type == "CONTAINS" and r.source_id in pkg_ids
        ]
        assert len(contains_from_pkg) == 6, (
            f"Expected 6 CONTAINS edges (App + Animal + Dog + AnimalService + Named + Walker), "
            f"got {len(contains_from_pkg)}"
        )


# ---------------------------------------------------------------------------
# No-duplicate-nodes assertions
# ---------------------------------------------------------------------------


class TestJavaNoDuplicateNodes:
    """Verify that no duplicated nodes or relationships are produced by the resolver."""

    def test_no_duplicate_external_module_nodes(self):
        """Two files importing the same external module produce exactly one ExternalModule.

        Unit test: verifies the resolver's internal deduplication dict works correctly.
        """
        file_a = _node("File", "Foo.java", "src/Foo.java")
        file_b = _node("File", "Bar.java", "src/Bar.java")

        # Both files import the same external library class
        raw_import_a = _raw_import("src/Foo.java", file_a.id, "org.springframework.stereotype.Service")
        raw_import_b = _raw_import("src/Bar.java", file_b.id, "org.springframework.stereotype.Service")

        ast_result = ASTResult(nodes=[file_a, file_b], raw_imports=[raw_import_a, raw_import_b])
        _, new_nodes = JavaCrossFileResolver().resolve(ast_result)

        ext_nodes = [n for n in new_nodes if n.type == "ExternalModule"]
        assert len(ext_nodes) == 1, (
            f"Expected 1 ExternalModule, got {len(ext_nodes)}: "
            f"{[n.name for n in ext_nodes]}"
        )
        assert ext_nodes[0].name == "org.springframework.stereotype.Service"

    def test_external_modules_unique_in_sample_project(self, sample_project_resolved):
        """Each external module_path appears at most once in resolver new_nodes.

        Guards against duplicates when the same stdlib class is imported from
        multiple project files.
        """
        _, _, new_nodes = sample_project_resolved
        ext_nodes = [n for n in new_nodes if n.type == "ExternalModule"]
        module_paths = [n.module_path for n in ext_nodes]
        duplicates = [p for p in module_paths if module_paths.count(p) > 1]
        assert not duplicates, f"Duplicate ExternalModule module_paths: {duplicates}"

    def test_no_duplicate_node_ids_in_new_nodes(self, sample_project_resolved):
        """All node IDs in the resolver's new_nodes list are unique."""
        _, _, new_nodes = sample_project_resolved
        ids = [n.id for n in new_nodes]
        assert len(ids) == len(set(ids)), (
            f"Duplicate IDs found in new_nodes: "
            f"{[i for i in ids if ids.count(i) > 1]}"
        )

    def test_no_duplicate_imports_relationships(self, sample_project_resolved):
        """No two IMPORTS relationships share the same (source_id, target_id) pair."""
        _, new_rels, _ = sample_project_resolved
        imports_rels = [(r.source_id, r.target_id) for r in new_rels if r.type == "IMPORTS"]
        duplicates = [p for p in imports_rels if imports_rels.count(p) > 1]
        assert not duplicates, f"Duplicate IMPORTS (source_id, target_id) pairs: {duplicates}"

    def test_no_duplicate_depends_on_relationships(self, sample_project_resolved):
        """No two DEPENDS_ON relationships share the same (source_id, target_id) pair."""
        _, new_rels, _ = sample_project_resolved
        depends_rels = [(r.source_id, r.target_id) for r in new_rels if r.type == "DEPENDS_ON"]
        duplicates = [p for p in depends_rels if depends_rels.count(p) > 1]
        assert not duplicates, f"Duplicate DEPENDS_ON (source_id, target_id) pairs: {duplicates}"

    def test_resolve_does_not_return_package_nodes(self, sample_project_resolved):
        """Regression: resolve() must not include Package nodes in new_nodes.

        Package nodes are already in ast_result.nodes (canonicalized by
        JavaParser._canonicalize_package_nodes). Re-emitting them here would
        cause duplicates when the orchestrator extends result.nodes with new_nodes.
        """
        _, _, new_nodes = sample_project_resolved
        package_nodes = [n for n in new_nodes if n.type == "Package"]
        assert not package_nodes, (
            f"resolve() returned {len(package_nodes)} unexpected Package node(s): "
            + ", ".join(n.module_path or n.name for n in package_nodes)
        )
