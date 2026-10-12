"""Tests for Java Package→CONTAINS→Class/Interface relationships via AnalysisOrchestrator.

T004: Reusable Java orchestrator test harness (fixtures + helper).
T006: Failing orchestrator coverage asserting containment relationships reach analysis output.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codeminer.components.analysis_orchestrator import AnalysisOrchestrator
from codeminer.parsing.discovery import FileDiscovery
from codeminer.parsing.java.cross_file_resolver import JavaCrossFileResolver
from codeminer.parsing.java.parser import JavaParser
from codeminer.parsing.models import ASTNode, ASTResult, Relationship

JAVA_FIXTURES_ROOT = (
    Path(__file__).parent / "parsing" / "java" / "fixtures" / "sample_project"
)


# ---------------------------------------------------------------------------
# T004: Fixtures and helper
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def java_sample_ast_result() -> ASTResult:
    """Parse all .java files from sample_project and return the combined ASTResult."""
    parser = JavaParser()
    java_files = list(JAVA_FIXTURES_ROOT.rglob("*.java"))
    assert java_files, f"No .java files found under {JAVA_FIXTURES_ROOT}"
    return parser.parse_files([str(f) for f in java_files], str(JAVA_FIXTURES_ROOT))


@pytest.fixture(scope="module")
def java_sample_resolved_result(
    java_sample_ast_result: ASTResult,
) -> tuple[ASTResult, list[Relationship], list[ASTNode]]:
    """Run JavaCrossFileResolver over the parsed result.

    Returns (merged_ast_result, new_rels, new_nodes).
    """
    resolver = JavaCrossFileResolver()
    new_rels, new_nodes = resolver.resolve(java_sample_ast_result)

    merged = ASTResult(
        file_info=java_sample_ast_result.file_info,
        nodes=list(java_sample_ast_result.nodes) + list(new_nodes),
        relationships=list(java_sample_ast_result.relationships) + list(new_rels),
        errors=java_sample_ast_result.errors,
        summary=java_sample_ast_result.summary,
        raw_imports=java_sample_ast_result.raw_imports,
        unresolved_references=java_sample_ast_result.unresolved_references,
    )
    return merged, new_rels, new_nodes


def make_orchestrator_with_mocks() -> AnalysisOrchestrator:
    """Create an AnalysisOrchestrator with mocked infrastructure and a real JavaParser."""
    mock_parser_registry = MagicMock()
    mock_parser_registry.get_parser_for_language.side_effect = lambda lang: (
        JavaParser() if lang == "java" else None
    )

    return AnalysisOrchestrator(
        parser_registry=mock_parser_registry,
        file_discovery=MagicMock(spec=FileDiscovery),
        graph_storage=MagicMock(),
        project_storage=MagicMock(),
        analysis_storage=MagicMock(),
    )


# ---------------------------------------------------------------------------
# T006: [US1] Containment relationship assertions — expect FAIL until resolver emits CONTAINS
# ---------------------------------------------------------------------------


class TestOrchestratorJavaContainmentUS1:
    """Verify that Package→CONTAINS→Class/Interface relationships reach analysis output.

    These tests are expected to FAIL until JavaCrossFileResolver emits CONTAINS edges.
    """

    def test_java_containment_rels_in_resolved_result(
        self,
        java_sample_resolved_result: tuple[
            ASTResult, list[Relationship], list[ASTNode]
        ],
    ) -> None:
        """At least one CONTAINS relationship has a Package node as source."""
        merged, new_rels, _ = java_sample_resolved_result

        package_ids = {n.id for n in merged.nodes if n.type == "Package"}
        contains_from_package = [
            r for r in new_rels if r.type == "CONTAINS" and r.source_id in package_ids
        ]
        assert contains_from_package, (
            "Expected at least one CONTAINS relationship originating from a Package node, "
            "but none were found. Implement Package→CONTAINS→Type in JavaCrossFileResolver."
        )

    def test_model_package_contains_animal_class(
        self,
        java_sample_resolved_result: tuple[
            ASTResult, list[Relationship], list[ASTNode]
        ],
    ) -> None:
        """com.example.model package has a CONTAINS edge to the Animal class."""
        merged, new_rels, _ = java_sample_resolved_result

        package_node = next(
            (
                n
                for n in merged.nodes
                if n.type == "Package" and n.name == "com.example.model"
            ),
            None,
        )
        assert (
            package_node is not None
        ), "Package node 'com.example.model' not found in merged result nodes."

        animal_node = next(
            (n for n in merged.nodes if n.type == "Class" and n.name == "Animal"),
            None,
        )
        assert (
            animal_node is not None
        ), "Class node 'Animal' not found in merged result nodes."

        has_contains = any(
            r.type == "CONTAINS"
            and r.source_id == package_node.id
            and r.target_id == animal_node.id
            for r in new_rels
        )
        assert has_contains, (
            f"Expected CONTAINS relationship from Package '{package_node.id}' "
            f"to Class '{animal_node.id}', but none found."
        )

    def test_service_package_contains_named_interface(
        self,
        java_sample_resolved_result: tuple[
            ASTResult, list[Relationship], list[ASTNode]
        ],
    ) -> None:
        """com.example.service package has a CONTAINS edge to the Named interface."""
        merged, new_rels, _ = java_sample_resolved_result

        package_node = next(
            (
                n
                for n in merged.nodes
                if n.type == "Package" and n.name == "com.example.service"
            ),
            None,
        )
        assert (
            package_node is not None
        ), "Package node 'com.example.service' not found in merged result nodes."

        named_node = next(
            (n for n in merged.nodes if n.type == "Interface" and n.name == "Named"),
            None,
        )
        assert (
            named_node is not None
        ), "Interface node 'Named' not found in merged result nodes."

        has_contains = any(
            r.type == "CONTAINS"
            and r.source_id == package_node.id
            and r.target_id == named_node.id
            for r in new_rels
        )
        assert has_contains, (
            f"Expected CONTAINS relationship from Package '{package_node.id}' "
            f"to Interface '{named_node.id}', but none found."
        )

    def test_all_java_packages_have_containment(
        self,
        java_sample_resolved_result: tuple[
            ASTResult, list[Relationship], list[ASTNode]
        ],
    ) -> None:
        """Every Package that owns at least one Class/Interface has a CONTAINS edge to each.

        Ownership is determined by matching module_path (package name) against the
        package declared in the same source file as the type node.
        """
        merged, new_rels, _ = java_sample_resolved_result

        # Build source_file → package_name lookup
        file_to_package: dict[str, str] = {
            n.source_file: n.name
            for n in merged.nodes
            if n.type == "Package" and n.source_file and n.name
        }

        # Map package name → Package node (canonical = first occurrence per package)
        package_nodes: dict[str, ASTNode] = {}
        for n in merged.nodes:
            if n.type == "Package" and n.name and n.name not in package_nodes:
                package_nodes[n.name] = n

        # Collect (package_name, type_node) pairs where the type lives in that package
        expected_pairs: list[tuple[str, ASTNode]] = []
        for node in merged.nodes:
            if node.type in ("Class", "Interface") and node.source_file:
                pkg_name = file_to_package.get(node.source_file)
                if pkg_name and pkg_name in package_nodes:
                    expected_pairs.append((pkg_name, node))

        assert expected_pairs, (
            "No Class/Interface nodes found belonging to any Package. "
            "Check fixture setup."
        )

        contains_set = {
            (r.source_id, r.target_id) for r in new_rels if r.type == "CONTAINS"
        }

        missing: list[str] = []
        for pkg_name, type_node in expected_pairs:
            pkg_node = package_nodes[pkg_name]
            if (pkg_node.id, type_node.id) not in contains_set:
                missing.append(
                    f"  Package '{pkg_name}' → {type_node.type} '{type_node.name}'"
                )

        assert not missing, (
            "Missing CONTAINS edges for the following package→type pairs:\n"
            + "\n".join(missing)
        )
