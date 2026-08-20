from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.functional_group import FunctionalGroup
from chem_wiki.modules.chemistry_core.identifiers import (
    FunctionalGroupId,
    StructureId,
    SubstanceId,
)
from chem_wiki.modules.chemistry_core.provenance import ProvenanceRef
from chem_wiki.modules.chemistry_core.structure import Structure, StructureFormat, StructureText


def test_structure_is_separate_and_keeps_opaque_text() -> None:
    structure_id = StructureId(uuid4())
    substance_id = SubstanceId(uuid4())
    provenance = ProvenanceRef(source_id="pubchem")

    structure = Structure(
        id=structure_id,
        substance_id=substance_id,
        format=StructureFormat(" smiles "),
        text=StructureText(" CCO "),
        provenance=(provenance,),
    )

    assert structure.id == structure_id
    assert structure.substance_id == substance_id
    assert structure.format.value == "smiles"
    assert structure.text.value == " CCO "
    assert structure.provenance == (provenance,)


@pytest.mark.parametrize("value", ["", " "])
def test_structure_format_rejects_blank_values(value: str) -> None:
    with pytest.raises(ValueError, match="format"):
        StructureFormat(value)


@pytest.mark.parametrize("value", ["", " "])
def test_structure_text_rejects_blank_values(value: str) -> None:
    with pytest.raises(ValueError, match="text"):
        StructureText(value)


def test_structure_is_immutable() -> None:
    structure = Structure(
        id=StructureId(uuid4()),
        substance_id=SubstanceId(uuid4()),
        format=StructureFormat("smiles"),
        text=StructureText("CCO"),
    )

    with pytest.raises(FrozenInstanceError):
        structure.text = StructureText("CO")  # type: ignore[misc]


def test_functional_group_is_a_minimal_catalog_entity() -> None:
    group_id = FunctionalGroupId(uuid4())

    group = FunctionalGroup(group_id, " hydroxyl ")

    assert group.id == group_id
    assert group.name == "hydroxyl"


def test_functional_group_name_must_not_be_blank() -> None:
    with pytest.raises(ValueError, match="name"):
        FunctionalGroup(FunctionalGroupId(uuid4()), " ")
