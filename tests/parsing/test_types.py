from codeminer.parsing.types import (
    NodeTypeDefinition,
    RelationshipTypeDefinition,
    CoreNodeType,
    CoreRelationshipType,
)


def test_node_type_definition_creation():
    ntd = NodeTypeDefinition(
        name="Class",
        language="python",
        category="structure",
        description="A Python class definition",
    )
    assert ntd.name == "Class"
    assert ntd.language == "python"


def test_relationship_type_definition_creation():
    rtd = RelationshipTypeDefinition(
        name="EXTENDS",
        language="python",
        category="inheritance",
        description="Class inheritance",
    )
    assert rtd.name == "EXTENDS"


def test_core_node_type_values():
    assert CoreNodeType.FILE == "File"
    assert CoreNodeType.CLASS == "Class"
    assert CoreNodeType.FUNCTION == "Function"
    assert CoreNodeType.PACKAGE == "Package"
    assert CoreNodeType.INTERFACE == "Interface"
    assert CoreNodeType.ENUM == "Enum"
    assert CoreNodeType.CONSTRUCTOR == "Constructor"
    assert CoreNodeType.VARIABLE == "Variable"
    assert CoreNodeType.METHOD == "Method"
    assert CoreNodeType.IMPORT == "Import"
    assert CoreNodeType.EXTERNAL_MODULE == "ExternalModule"


def test_core_relationship_type_values():
    assert CoreRelationshipType.CONTAINS == "CONTAINS"
    assert CoreRelationshipType.EXTENDS == "EXTENDS"


def test_defined_in_removed_from_core_relationship_types():
    assert not hasattr(CoreRelationshipType, "DEFINED_IN")
    assert "DEFINED_IN" not in {m.value for m in CoreRelationshipType}


def test_all_emitted_relationship_types_in_enum():
    expected = {"CONTAINS", "EXTENDS", "IMPLEMENTS", "CALLS", "DEPENDS_ON", "USES", "IMPORTS"}
    actual = {m.value for m in CoreRelationshipType}
    assert expected == actual
