from types import SimpleNamespace
from uuid import UUID

from chem_wiki.modules.knowledge_catalog import PostgresCatalogReader
from chem_wiki.modules.knowledge_catalog.read_model import (
    CatalogReactionParticipantResult,
    CatalogSpeciesResult,
)


class SessionStub:
    def __init__(self, rows: list[tuple[SimpleNamespace, SimpleNamespace]]) -> None:
        self._rows = rows

    def execute(self, statement):
        return self._rows


def _species(
    *,
    consolidated_id: str,
    formula: str,
    charge: int,
    entity_kind: str,
    composition: dict[str, int],
    classifications: list[str],
) -> SimpleNamespace:
    return SimpleNamespace(
        consolidated_id=consolidated_id,
        application_id=UUID(int=len(consolidated_id)),
        entity_kind=entity_kind,
        name_zh=consolidated_id,
        name_en=None,
        formula=formula,
        charge=charge,
        composition=composition,
        aliases=[],
        chemical_classifications=classifications,
    )


def _projection(*, rank: int = 1, priority: str = "core") -> SimpleNamespace:
    return SimpleNamespace(
        primary_category="salt",
        tags=[],
        default_priority=priority,
        default_palette_rank=rank,
        molecular_suitability="recommended",
        ionic_suitability="available",
        net_ionic_suitability="available",
    )


def test_catalog_species_read_dto_exposes_composition_and_classifications() -> None:
    assert "composition" in CatalogSpeciesResult.model_fields
    assert "chemical_classifications" in CatalogSpeciesResult.model_fields


def test_catalog_reaction_participant_exposes_canonical_species_display_fields() -> None:
    assert {"name_zh", "formula", "charge"} <= set(CatalogReactionParticipantResult.model_fields)


def test_catalog_reader_resolves_known_species_by_composition_charge_and_kind() -> None:
    sodium_sulfate = _species(
        consolidated_id="species:sodium-sulfate",
        formula="Na2SO4",
        charge=0,
        entity_kind="substance",
        composition={"Na": 2, "S": 1, "O": 4},
        classifications=["salt", "strong_electrolyte"],
    )
    sodium_ion = _species(
        consolidated_id="species:sodium-ion",
        formula="Na",
        charge=1,
        entity_kind="ion",
        composition={"Na": 1},
        classifications=[],
    )
    reader = PostgresCatalogReader(
        SessionStub(
            [
                (sodium_sulfate, _projection()),
                (sodium_ion, _projection()),
            ]
        )
    )

    matches = reader.search_species(
        composition={"Na": 2, "S": 1, "O": 4},
        total_charge=0,
        entity_kind="substance",
        limit=5,
    )

    assert [match.formula for match in matches] == ["Na2SO4"]
    assert matches[0].composition == {"Na": 2, "S": 1, "O": 4}
    assert matches[0].chemical_classifications == ["salt", "strong_electrolyte"]


def test_catalog_reader_returns_multiple_or_no_known_composition_matches() -> None:
    butenes = [
        _species(
            consolidated_id=f"species:butene-{index}",
            formula="C4H8",
            charge=0,
            entity_kind="substance",
            composition={"C": 4, "H": 8},
            classifications=["organic"],
        )
        for index in range(2)
    ]
    reader = PostgresCatalogReader(SessionStub([(item, _projection()) for item in butenes]))

    assert (
        len(
            reader.search_species(
                composition={"C": 4, "H": 8},
                total_charge=0,
                entity_kind="substance",
                limit=5,
            )
        )
        == 2
    )
    assert (
        reader.search_species(
            composition={"X": 1},
            total_charge=0,
            entity_kind="substance",
            limit=5,
        )
        == []
    )


def test_catalog_reader_hydrates_exact_application_ids_without_normal_search_ranking() -> None:
    water = _species(
        consolidated_id="species:water",
        formula="H2O",
        charge=0,
        entity_kind="substance",
        composition={"H": 2, "O": 1},
        classifications=[],
    )
    long_tail = _species(
        consolidated_id="species:long-tail",
        formula="C7H8",
        charge=0,
        entity_kind="substance",
        composition={"C": 7, "H": 8},
        classifications=["organic"],
    )
    reader = PostgresCatalogReader(
        SessionStub([(water, _projection()), (long_tail, _projection())])
    )

    matches = reader.search_species(
        application_ids=[long_tail.application_id],
        limit=50,
    )

    assert [match.application_id for match in matches] == [long_tail.application_id]


def test_catalog_completion_returns_strontium_substances_instead_of_exact_ion_echo() -> None:
    strontium = _species(
        consolidated_id="species:strontium",
        formula="Sr",
        charge=0,
        entity_kind="substance",
        composition={"Sr": 1},
        classifications=["elemental_substance"],
    )
    strontium_chloride = _species(
        consolidated_id="species:strontium-chloride",
        formula="SrCl2",
        charge=0,
        entity_kind="substance",
        composition={"Sr": 1, "Cl": 2},
        classifications=["salt"],
    )
    strontium_ion = _species(
        consolidated_id="species:strontium-ion",
        formula="Sr",
        charge=2,
        entity_kind="ion",
        composition={"Sr": 1},
        classifications=[],
    )
    reader = PostgresCatalogReader(
        SessionStub(
            [
                (strontium_chloride, _projection(rank=4)),
                (strontium_ion, _projection(rank=2)),
                (strontium, _projection(rank=3)),
            ]
        )
    )

    matches = reader.complete_species(composition={"Sr": 1}, limit=10)

    assert [match.formula for match in matches] == ["Sr", "SrCl2"]
    assert all(match.entity_kind == "substance" for match in matches)


def test_catalog_completion_ranks_exact_strontium_and_sodium_sulfates_first() -> None:
    candidates = [
        _species(
            consolidated_id="species:strontium-sulfate",
            formula="SrSO4",
            charge=0,
            entity_kind="substance",
            composition={"Sr": 1, "S": 1, "O": 4},
            classifications=["salt"],
        ),
        _species(
            consolidated_id="species:strontium-sulfite",
            formula="SrSO3",
            charge=0,
            entity_kind="substance",
            composition={"Sr": 1, "S": 1, "O": 3},
            classifications=["salt"],
        ),
        _species(
            consolidated_id="species:sodium-sulfate",
            formula="Na2SO4",
            charge=0,
            entity_kind="substance",
            composition={"Na": 2, "S": 1, "O": 4},
            classifications=["salt"],
        ),
        _species(
            consolidated_id="species:sodium-hydrogen-sulfate",
            formula="NaHSO4",
            charge=0,
            entity_kind="substance",
            composition={"Na": 1, "H": 1, "S": 1, "O": 4},
            classifications=["salt"],
        ),
    ]
    reader = PostgresCatalogReader(
        SessionStub([(candidate, _projection(rank=index)) for index, candidate in enumerate(candidates)])
    )

    assert reader.complete_species(
        composition={"Sr": 1, "S": 1, "O": 4}, limit=10
    )[0].formula == "SrSO4"
    assert reader.complete_species(
        composition={"Na": 2, "S": 1, "O": 4}, limit=10
    )[0].formula == "Na2SO4"


def test_catalog_completion_has_explicit_empty_and_deterministic_tie_breaks() -> None:
    candidates = [
        _species(
            consolidated_id=consolidated_id,
            formula="SrX",
            charge=0,
            entity_kind="substance",
            composition={"Sr": 1, "X": 1},
            classifications=[],
        )
        for consolidated_id in ["species:zeta", "species:alpha"]
    ]
    reader = PostgresCatalogReader(
        SessionStub([(candidate, _projection(rank=1)) for candidate in candidates])
    )

    assert [item.consolidated_id for item in reader.complete_species(
        composition={"Sr": 1}, limit=10
    )] == ["species:alpha", "species:zeta"]
    assert reader.complete_species(composition={"Xe": 2}, limit=10) == []
