from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.composition import ChemicalFormula, CompositionEntry
from chem_wiki.modules.chemistry_core.element import AtomicNumber, Element, ElementSymbol
from chem_wiki.modules.chemistry_core.identifiers import ElementId, IonId, SubstanceId
from chem_wiki.modules.chemistry_core.ion import ElectricCharge, Ion
from chem_wiki.modules.chemistry_core.provenance import ProvenanceRef
from chem_wiki.modules.chemistry_core.substance import Substance


def test_element_keeps_stable_identity_and_normalized_names() -> None:
    element_id = ElementId(uuid4())

    element = Element(
        id=element_id,
        atomic_number=AtomicNumber(17),
        symbol=ElementSymbol("Cl"),
        name_zh=" 氯 ",
        name_en=" chlorine ",
    )

    assert element.id == element_id
    assert element.name_zh == "氯"
    assert element.name_en == "chlorine"


@pytest.mark.parametrize(
    ("name_zh", "name_en", "expected_field"),
    [(" ", "chlorine", "name_zh"), ("氯", " ", "name_en")],
)
def test_element_names_must_not_be_blank(name_zh: str, name_en: str, expected_field: str) -> None:
    with pytest.raises(ValueError, match=expected_field):
        Element(
            id=ElementId(uuid4()),
            atomic_number=AtomicNumber(17),
            symbol=ElementSymbol("Cl"),
            name_zh=name_zh,
            name_en=name_en,
        )


def test_element_is_immutable() -> None:
    element = Element(
        id=ElementId(uuid4()),
        atomic_number=AtomicNumber(17),
        symbol=ElementSymbol("Cl"),
        name_zh="氯",
        name_en="chlorine",
    )

    with pytest.raises(FrozenInstanceError):
        element.name_en = "other"  # type: ignore[misc]


@pytest.mark.parametrize("value", [0, -1])
def test_atomic_number_must_be_positive(value: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        AtomicNumber(value)


@pytest.mark.parametrize("value", ["", "cl", "CL"])
def test_element_symbol_rejects_invalid_spelling(value: str) -> None:
    with pytest.raises(ValueError, match="symbol"):
        ElementSymbol(value)


def test_formula_is_opaque_but_normalized_and_not_blank() -> None:
    assert ChemicalFormula(" NH4+ ").value == "NH4+"

    with pytest.raises(ValueError, match="formula"):
        ChemicalFormula(" ")


@pytest.mark.parametrize("amount", [Decimal(0), Decimal(-1)])
def test_composition_amount_must_be_positive(amount: Decimal) -> None:
    with pytest.raises(ValueError, match="amount"):
        CompositionEntry(ElementId(uuid4()), amount)


def test_composition_entry_keeps_fact_provenance() -> None:
    provenance = ProvenanceRef(source_id="nist-webbook")

    entry = CompositionEntry(
        element_id=ElementId(uuid4()),
        amount=Decimal(2),
        provenance=(provenance,),
    )

    assert entry.provenance == (provenance,)


def test_substance_requires_composition() -> None:
    with pytest.raises(ValueError, match="composition"):
        Substance(SubstanceId(uuid4()), ChemicalFormula("H2O"), ())


def test_ion_requires_composition() -> None:
    with pytest.raises(ValueError, match="composition"):
        Ion(IonId(uuid4()), ChemicalFormula("Cl-"), (), ElectricCharge(-1))


def test_ion_requires_nonzero_charge() -> None:
    with pytest.raises(ValueError, match="charge"):
        ElectricCharge(0)


def test_substance_and_ion_share_composition_without_a_species_base() -> None:
    entry = CompositionEntry(ElementId(uuid4()), Decimal(1))

    substance = Substance(SubstanceId(uuid4()), ChemicalFormula("HCl"), (entry,))
    ion = Ion(IonId(uuid4()), ChemicalFormula("Cl-"), (entry,), ElectricCharge(-1))

    assert substance.composition == ion.composition
