from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.modules.element_data import (
    ElementDataBase,
    bootstrap_element_identities,
    import_pubchem_elements,
)
from chem_wiki.modules.element_data.nist_asd import NistAsdAdapter
from chem_wiki.modules.element_data.pubchem import PubChemAdapter

pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).parents[2]
NIST_FIXTURE = Path(__file__).parents[1] / "fixtures" / "nist_asd_ionization_h_he.csv"
FIRST_RETRIEVAL = datetime(2026, 8, 20, 14, 30, tzinfo=UTC)
SECOND_RETRIEVAL = datetime(2026, 8, 20, 15, 30, tzinfo=UTC)

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
    try:
        return import_module("chem_wiki.modules.element_data.nist_import")
    except ModuleNotFoundError as exc:
        pytest.fail(f"NIST ASD importer is missing: {exc}")


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


def _nist_adapter(retrieved_at: datetime) -> NistAsdAdapter:
    return NistAsdAdapter(
        fetch_text=lambda _url, _timeout: NIST_FIXTURE.read_text(encoding="utf-8"),
        clock=lambda: retrieved_at,
    )


def _count(session: Session, table_name: str) -> int:
    table = ElementDataBase.metadata.tables[table_name]
    return session.scalar(select(func.count()).select_from(table)) or 0


def test_nist_calibrates_pubchem_without_changing_identity_and_is_idempotent() -> None:
    importer = _load_importer()
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine, Session(engine) as session:
        bootstrap_element_identities(session)
        session.commit()
        identities_before = session.execute(
            select(
                tables["element"].c.id,
                tables["element"].c.atomic_number,
                tables["element"].c.symbol,
                tables["element"].c.name_zh,
                tables["element"].c.name_en,
            )
            .where(tables["element"].c.atomic_number.in_([1, 2]))
            .order_by(tables["element"].c.atomic_number)
        ).all()

        import_pubchem_elements(
            session,
            adapter=PubChemAdapter(
                fetch_json=lambda _url, _timeout: PUBCHEM_HYDROGEN,
                clock=lambda: FIRST_RETRIEVAL,
            ),
            atomic_numbers={1},
        )
        session.commit()
        pubchem_claim_id = session.scalar(
            select(tables["element_published_value"].c.claim_id).where(
                tables["element_published_value"].c.element_id == identities_before[0].id,
                tables["element_published_value"].c.field_name == "first_ionization_energy",
            )
        )

        first_result = importer.import_nist_calibrations(
            session,
            adapter=_nist_adapter(FIRST_RETRIEVAL),
            atomic_numbers={1, 2},
        )
        session.commit()

        assert tuple(element_id.value for element_id in first_result.element_ids) == tuple(
            row.id for row in identities_before
        )
        assert first_result.source_records_created == 2
        assert first_result.claims_created == 2
        assert first_result.publications_changed == 2
        assert (
            session.execute(
                select(
                    tables["element"].c.id,
                    tables["element"].c.atomic_number,
                    tables["element"].c.symbol,
                    tables["element"].c.name_zh,
                    tables["element"].c.name_en,
                )
                .where(tables["element"].c.atomic_number.in_([1, 2]))
                .order_by(tables["element"].c.atomic_number)
            ).all()
            == identities_before
        )

        nist_source = (
            session.execute(
                select(tables["element_source"]).where(
                    tables["element_source"].c.source_key == "nist-asd-ionization-energies"
                )
            )
            .one()
            ._mapping
        )
        assert nist_source["publisher"] == "National Institute of Standards and Technology"
        assert nist_source["source_type"] == "database"

        hydrogen_record = (
            session.execute(
                select(tables["element_source_record"]).where(
                    tables["element_source_record"].c.source_id == nist_source["id"],
                    tables["element_source_record"].c.record_key == "H I",
                )
            )
            .one()
            ._mapping
        )
        assert hydrogen_record["source_version"] == "nist-asd-5.12"
        assert hydrogen_record["retrieved_at"] == FIRST_RETRIEVAL
        assert hydrogen_record["raw_payload"]["References"] == "HDEL"
        assert (
            "NIST Atomic Spectra Database (ver. 5.12)"
            in hydrogen_record["raw_payload"]["ASD Citation"]
        )

        nist_claim = (
            session.execute(
                select(tables["element_claim"]).where(
                    tables["element_claim"].c.source_record_id == hydrogen_record["id"]
                )
            )
            .one()
            ._mapping
        )
        assert nist_claim["field_name"] == "first_ionization_energy"
        assert nist_claim["raw_value"] == "13.598434599702"
        assert nist_claim["normalized_numeric"] == Decimal("13.598434599702")
        assert nist_claim["canonical_unit"] == "eV"
        assert nist_claim["uncertainty"] == Decimal("0.000000000012")
        assert nist_claim["qualifier"] == "()"

        publication = (
            session.execute(
                select(tables["element_published_value"]).where(
                    tables["element_published_value"].c.element_id == identities_before[0].id,
                    tables["element_published_value"].c.field_name == "first_ionization_energy",
                )
            )
            .one()
            ._mapping
        )
        assert publication["claim_id"] == nist_claim["id"]
        assert publication["claim_id"] != pubchem_claim_id
        assert publication["policy_version"] == "m02-nist-asd-v1"
        assert publication["selected_at"] == FIRST_RETRIEVAL
        assert _count(session, "element_claim") == 118 * 4 + 6 + 2
        assert session.scalar(
            select(tables["element_property"].c.first_ionization_energy_value).where(
                tables["element_property"].c.element_id == identities_before[0].id
            )
        ) == Decimal("13.598")

        counts_after_first = {
            table_name: _count(session, table_name)
            for table_name in (
                "element",
                "element_source",
                "element_source_record",
                "element_claim",
                "element_published_value",
            )
        }
        second_result = importer.import_nist_calibrations(
            session,
            adapter=_nist_adapter(SECOND_RETRIEVAL),
            atomic_numbers={1, 2},
        )
        session.commit()

        assert second_result.element_ids == first_result.element_ids
        assert second_result.source_records_created == 0
        assert second_result.claims_created == 0
        assert second_result.publications_changed == 0
        assert {
            table_name: _count(session, table_name) for table_name in counts_after_first
        } == counts_after_first
        assert (
            session.scalar(
                select(tables["element_published_value"].c.selected_at).where(
                    tables["element_published_value"].c.element_id == identities_before[0].id,
                    tables["element_published_value"].c.field_name == "first_ionization_energy",
                )
            )
            == FIRST_RETRIEVAL
        )

        pubchem_after_nist = import_pubchem_elements(
            session,
            adapter=PubChemAdapter(
                fetch_json=lambda _url, _timeout: PUBCHEM_HYDROGEN,
                clock=lambda: SECOND_RETRIEVAL,
            ),
            atomic_numbers={1},
        )
        session.commit()
        assert pubchem_after_nist.publications_changed == 0
        protected_publication = (
            session.execute(
                select(tables["element_published_value"]).where(
                    tables["element_published_value"].c.element_id == identities_before[0].id,
                    tables["element_published_value"].c.field_name == "first_ionization_energy",
                )
            )
            .one()
            ._mapping
        )
        assert protected_publication["policy_version"] == "m02-nist-asd-v1"
