from types import SimpleNamespace
from uuid import UUID

from chem_wiki.modules.knowledge_catalog import PostgresCatalogReader
from chem_wiki.modules.knowledge_catalog.read_model import CatalogSpeciesResult


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


def _projection() -> SimpleNamespace:
    return SimpleNamespace(
        primary_category="salt",
        tags=[],
        default_priority="core",
        default_palette_rank=1,
        molecular_suitability="recommended",
        ionic_suitability="available",
        net_ionic_suitability="available",
    )


def test_catalog_species_read_dto_exposes_composition_and_classifications() -> None:
    assert "composition" in CatalogSpeciesResult.model_fields
    assert "chemical_classifications" in CatalogSpeciesResult.model_fields


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
