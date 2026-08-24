from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.modules.chemistry_core import (
    AtomicNumber,
    Element,
    ElementId,
    ElementSymbol,
)
from chem_wiki.modules.element_data import ElementDataBase
from chem_wiki.modules.element_data.pubchem import PubChemAdapter

pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).parents[2]
PUBCHEM_COLUMNS = [
    "AtomicNumber",
    "Symbol",
    "Name",
    "AtomicMass",
    "CPKHexColor",
    "ElectronConfiguration",
    "Electronegativity",
    "AtomicRadius",
    "IonizationEnergy",
    "ElectronAffinity",
    "OxidationStates",
    "StandardState",
    "MeltingPoint",
    "BoilingPoint",
    "Density",
    "GroupBlock",
    "YearDiscovered",
]
PUBCHEM_HYDROGEN: dict[str, Any] = {
    "Table": {
        "Columns": {"Column": PUBCHEM_COLUMNS},
        "Row": [
            {
                "Cell": [
                    "1",
                    "H",
                    "Hydrogen",
                    "1.0080",
                    "FFFFFF",
                    "1s1",
                    "2.2",
                    "120",
                    "13.598",
                    "0.754",
                    "+1, -1",
                    "Gas",
                    "13.81",
                    "20.28",
                    "0.00008988",
                    "Nonmetal",
                    "1766",
                ]
            }
        ],
    }
}


def _load_importer() -> Any:
    return import_module("chem_wiki.modules.element_data.identity_bootstrap")


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


@contextmanager
def _migrated_engine() -> Iterator[Engine]:
    config = _alembic_config()
    engine = create_engine(Settings().database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    try:
        yield engine
    finally:
        command.downgrade(config, "base")
        engine.dispose()


def _count(session: Session, table_name: str) -> int:
    table = ElementDataBase.metadata.tables[table_name]
    return session.scalar(select(func.count()).select_from(table)) or 0


def test_bootstrap_persists_118_complete_identities_with_field_provenance() -> None:
    importer = _load_importer()
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine, Session(engine) as session:
        result = importer.bootstrap_element_identities(session)
        session.commit()

        assert result.elements_created == 118
        assert result.source_records_created == 236
        assert result.claims_created == 472
        assert result.publications_changed == 472
        assert len(result.element_ids) == 118
        assert len(set(result.element_ids)) == 118

        assert _count(session, "element") == 118
        assert _count(session, "element_source") == 3
        assert _count(session, "element_source_record") == 236
        assert _count(session, "element_claim") == 472
        assert _count(session, "element_published_value") == 472
        assert _count(session, "element_property") == 0

        rows = session.execute(
            select(tables["element"]).order_by(tables["element"].c.atomic_number)
        ).mappings()
        elements = [
            Element(
                id=ElementId(row["id"]),
                atomic_number=AtomicNumber(row["atomic_number"]),
                symbol=ElementSymbol(row["symbol"]),
                name_zh=row["name_zh"],
                name_en=row["name_en"],
            )
            for row in rows
        ]
        assert [element.atomic_number.value for element in elements] == list(range(1, 119))
        assert len({element.symbol.value for element in elements}) == 118
        assert len({element.name_zh for element in elements}) == 118
        assert len({element.name_en for element in elements}) == 118
        assert (elements[0].symbol.value, elements[0].name_zh, elements[0].name_en) == (
            "H",
            "氢",
            "hydrogen",
        )
        assert (elements[-1].symbol.value, elements[-1].name_zh, elements[-1].name_en) == (
            "Og",
            "鿫",
            "oganesson",
        )

        provenance = session.execute(
            select(
                tables["element"].c.atomic_number,
                tables["element_published_value"].c.field_name,
                tables["element_source"].c.source_key,
                tables["element_published_value"].c.selection_method,
            )
            .join(
                tables["element_published_value"],
                tables["element_published_value"].c.element_id == tables["element"].c.id,
            )
            .join(
                tables["element_claim"],
                tables["element_claim"].c.id == tables["element_published_value"].c.claim_id,
            )
            .join(
                tables["element_source_record"],
                tables["element_source_record"].c.id == tables["element_claim"].c.source_record_id,
            )
            .join(
                tables["element_source"],
                tables["element_source"].c.id == tables["element_source_record"].c.source_id,
            )
            .where(tables["element"].c.atomic_number.in_([1, 117, 118]))
        ).all()
        by_element_field = {
            (row.atomic_number, row.field_name): (row.source_key, row.selection_method)
            for row in provenance
        }
        for atomic_number in (1, 117, 118):
            for field_name in ("atomic_number", "symbol", "name_en"):
                assert by_element_field[(atomic_number, field_name)] == (
                    "iupac-periodic-table-2022",
                    "authority_policy",
                )
        assert by_element_field[(1, "name_zh")] == (
            "periodic-table-pro-zhcn",
            "manual",
        )
        assert by_element_field[(117, "name_zh")] == (
            "cnctst-official-element-names-2017",
            "authority_policy",
        )
        assert by_element_field[(118, "name_zh")] == (
            "cnctst-official-element-names-2017",
            "authority_policy",
        )


def test_full_identity_reimport_is_idempotent_and_preserves_element_ids() -> None:
    importer = _load_importer()
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine, Session(engine) as session:
        first = importer.bootstrap_element_identities(session)
        session.commit()
        ids_after_first = dict(
            session.execute(select(tables["element"].c.atomic_number, tables["element"].c.id)).all()
        )
        counts_after_first = {
            table_name: _count(session, table_name)
            for table_name in (
                "element",
                "element_property",
                "element_source",
                "element_source_record",
                "element_claim",
                "element_published_value",
            )
        }

        second = importer.bootstrap_element_identities(session)
        session.commit()

        assert first.element_ids == second.element_ids
        assert second.elements_created == 0
        assert second.source_records_created == 0
        assert second.claims_created == 0
        assert second.publications_changed == 0
        assert (
            dict(
                session.execute(
                    select(tables["element"].c.atomic_number, tables["element"].c.id)
                ).all()
            )
            == ids_after_first
        )
        assert {
            table_name: _count(session, table_name) for table_name in counts_after_first
        } == counts_after_first


def test_pubchem_enriches_a_bootstrapped_element_without_changing_identity() -> None:
    importer = _load_importer()
    pubchem_importer = import_module("chem_wiki.modules.element_data.pubchem_import")
    tables = ElementDataBase.metadata.tables
    retrieved_at = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)
    adapter = PubChemAdapter(
        fetch_json=lambda _url, _timeout: PUBCHEM_HYDROGEN,
        clock=lambda: retrieved_at,
    )

    with _migrated_engine() as engine, Session(engine) as session:
        importer.bootstrap_element_identities(session)
        session.commit()
        identity_before = (
            session.execute(select(tables["element"]).where(tables["element"].c.atomic_number == 1))
            .mappings()
            .one()
        )
        identity_publications_before = dict(
            session.execute(
                select(
                    tables["element_published_value"].c.field_name,
                    tables["element_published_value"].c.claim_id,
                ).where(
                    tables["element_published_value"].c.element_id == identity_before["id"],
                    tables["element_published_value"].c.field_name.in_(
                        ["atomic_number", "symbol", "name_zh", "name_en"]
                    ),
                )
            ).all()
        )

        enrichment = pubchem_importer.import_pubchem_elements(
            session,
            adapter=adapter,
            atomic_numbers={1},
        )
        session.commit()

        identity_after = (
            session.execute(select(tables["element"]).where(tables["element"].c.atomic_number == 1))
            .mappings()
            .one()
        )
        assert dict(identity_after) == dict(identity_before)
        assert enrichment.element_ids == (ElementId(identity_before["id"]),)
        assert enrichment.publications_changed == 3
        assert (
            dict(
                session.execute(
                    select(
                        tables["element_published_value"].c.field_name,
                        tables["element_published_value"].c.claim_id,
                    ).where(
                        tables["element_published_value"].c.element_id == identity_before["id"],
                        tables["element_published_value"].c.field_name.in_(
                            ["atomic_number", "symbol", "name_zh", "name_en"]
                        ),
                    )
                ).all()
            )
            == identity_publications_before
        )
        assert {
            row.field_name
            for row in session.execute(
                select(tables["element_published_value"].c.field_name).where(
                    tables["element_published_value"].c.element_id == identity_before["id"],
                    tables["element_published_value"].c.policy_version == "m02-pubchem-v1",
                )
            )
        } == {"electronegativity", "first_ionization_energy", "atomic_radius"}
