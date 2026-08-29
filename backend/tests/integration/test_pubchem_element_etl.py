from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.modules.chemistry_core import ElementId
from chem_wiki.modules.element_data import ElementDataBase, bootstrap_element_identities
from chem_wiki.modules.element_data.pubchem import PubChemAdapter

pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).parents[2]
FIRST_RETRIEVAL = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)
SECOND_RETRIEVAL = datetime(2026, 8, 20, 10, 30, tzinfo=UTC)

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
PUBCHEM_PAYLOAD: dict[str, Any] = {
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
        return import_module("chem_wiki.modules.element_data.pubchem_import")
    except ModuleNotFoundError as exc:
        pytest.fail(f"PubChem persistence importer is missing: {exc}")


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


def _seed_canonical_hydrogen(session: Session) -> ElementId:
    tables = ElementDataBase.metadata.tables
    element_id = ElementId(uuid4())
    source_id = uuid4()
    source_record_id = uuid4()

    session.execute(
        tables["element_source"]
        .insert()
        .values(
            id=source_id,
            source_key="authoritative-identity-seed",
            title="Authoritative identity test seed",
            source_type="manual",
            reuse_policy="allowed",
        )
    )
    session.execute(
        tables["element_source_record"]
        .insert()
        .values(
            id=source_record_id,
            source_id=source_id,
            source_version="test-v1",
            record_key="1",
            source_url="https://example.test/identity/1",
            retrieved_at=FIRST_RETRIEVAL,
            content_sha256="a" * 64,
            raw_payload={"atomic_number": 1, "symbol": "H"},
        )
    )
    session.execute(
        tables["element"]
        .insert()
        .values(
            id=element_id.value,
            atomic_number=1,
            symbol="H",
            name_zh="氢",
            name_en="hydrogen",
        )
    )
    claim_values = {
        "atomic_number": {"raw_value": "1", "normalized_integer": 1},
        "symbol": {"raw_value": "H", "normalized_text": "H"},
        "name_zh": {"raw_value": "氢", "normalized_text": "氢"},
        "name_en": {"raw_value": "hydrogen", "normalized_text": "hydrogen"},
    }
    for field_name, values in claim_values.items():
        claim_id = uuid4()
        session.execute(
            tables["element_claim"]
            .insert()
            .values(
                id=claim_id,
                element_id=element_id.value,
                source_record_id=source_record_id,
                field_name=field_name,
                verification_status="verified",
                transform_version="test-v1",
                **values,
            )
        )
        session.execute(
            tables["element_published_value"]
            .insert()
            .values(
                element_id=element_id.value,
                field_name=field_name,
                claim_id=claim_id,
                selection_method="authority_policy",
                policy_version="identity-test-v1",
                selected_by="policy:identity-test-v1",
                selection_reason="authoritative identity test seed",
                selected_at=FIRST_RETRIEVAL,
            )
        )
    session.commit()
    return element_id


def _adapter(retrieved_at: datetime) -> PubChemAdapter:
    return PubChemAdapter(
        fetch_json=lambda _url, _timeout: PUBCHEM_PAYLOAD,
        clock=lambda: retrieved_at,
    )


def _identity_adapter(atomic_number: int, symbol: str, name: str) -> PubChemAdapter:
    cells = list(PUBCHEM_PAYLOAD["Table"]["Row"][0]["Cell"])
    cells[0:3] = [str(atomic_number), symbol, name]
    payload = {
        "Table": {
            "Columns": {"Column": PUBCHEM_COLUMNS},
            "Row": [{"Cell": cells}],
        }
    }
    return PubChemAdapter(fetch_json=lambda _url, _timeout: payload, clock=lambda: FIRST_RETRIEVAL)


def _count(session: Session, table_name: str) -> int:
    table = ElementDataBase.metadata.tables[table_name]
    return session.scalar(select(func.count()).select_from(table)) or 0


def test_pubchem_import_persists_provenance_and_is_idempotent() -> None:
    importer = _load_importer()
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine, Session(engine) as session:
        original_element_id = _seed_canonical_hydrogen(session)

        first_result = importer.import_pubchem_elements(
            session,
            adapter=_adapter(FIRST_RETRIEVAL),
            atomic_numbers={1},
        )
        session.commit()

        assert first_result.element_ids == (original_element_id,)
        assert first_result.source_records_created == 1
        assert first_result.claims_created == 6
        assert first_result.publications_changed == 3
        assert (
            session.scalar(
                select(tables["element"].c.id).where(tables["element"].c.atomic_number == 1)
            )
            == original_element_id.value
        )

        source = (
            session.execute(
                select(tables["element_source"]).where(
                    tables["element_source"].c.source_key == "pubchem-periodic-table"
                )
            )
            .one()
            ._mapping
        )
        assert source["publisher"] == "National Center for Biotechnology Information"
        assert source["reuse_policy"] == "review_required"
        assert source["license_code"] is None

        source_record = (
            session.execute(
                select(tables["element_source_record"]).where(
                    tables["element_source_record"].c.source_id == source["id"]
                )
            )
            .one()
            ._mapping
        )
        assert source_record["raw_payload"] == dict(
            zip(PUBCHEM_COLUMNS, PUBCHEM_PAYLOAD["Table"]["Row"][0]["Cell"])
        )
        assert source_record["retrieved_at"] == FIRST_RETRIEVAL

        pubchem_claims = session.execute(
            select(tables["element_claim"]).where(
                tables["element_claim"].c.source_record_id == source_record["id"]
            )
        ).all()
        assert {row._mapping["field_name"] for row in pubchem_claims} == {
            "atomic_number",
            "symbol",
            "name_en",
            "electronegativity",
            "first_ionization_energy",
            "atomic_radius",
        }
        assert {row._mapping["verification_status"] for row in pubchem_claims} == {"verified"}

        selected = session.execute(
            select(tables["element_published_value"]).where(
                tables["element_published_value"].c.element_id == original_element_id.value,
                tables["element_published_value"].c.policy_version == "m02-pubchem-v1",
            )
        ).all()
        assert {row._mapping["field_name"] for row in selected} == {
            "electronegativity",
            "first_ionization_energy",
            "atomic_radius",
        }
        selected_at = {row._mapping["selected_at"] for row in selected}
        assert selected_at == {FIRST_RETRIEVAL}

        properties = (
            session.execute(
                select(tables["element_property"]).where(
                    tables["element_property"].c.element_id == original_element_id.value
                )
            )
            .one()
            ._mapping
        )
        assert properties["electronegativity_value"] == Decimal("2.200")
        assert properties["electronegativity_scale"] == "Pauling"
        assert properties["first_ionization_energy_value"] == Decimal("13.598")
        assert properties["first_ionization_energy_unit"] == "eV"
        assert properties["atomic_radius_value"] == Decimal("120.000")
        assert properties["atomic_radius_unit"] == "pm"
        assert properties["atomic_radius_qualifier"] == "atomic"

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

        second_result = importer.import_pubchem_elements(
            session,
            adapter=_adapter(SECOND_RETRIEVAL),
            atomic_numbers={1},
        )
        session.commit()

        assert second_result.element_ids == (original_element_id,)
        assert second_result.source_records_created == 0
        assert second_result.claims_created == 0
        assert second_result.publications_changed == 0
        assert {
            table_name: _count(session, table_name) for table_name in counts_after_first
        } == counts_after_first
        assert (
            session.scalar(
                select(tables["element"].c.id).where(tables["element"].c.atomic_number == 1)
            )
            == original_element_id.value
        )
        assert {
            row._mapping["selected_at"]
            for row in session.execute(
                select(tables["element_published_value"]).where(
                    tables["element_published_value"].c.element_id == original_element_id.value,
                    tables["element_published_value"].c.policy_version == "m02-pubchem-v1",
                )
            )
        } == {FIRST_RETRIEVAL}


def test_pubchem_import_refuses_to_create_canonical_identity() -> None:
    importer = _load_importer()
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine, Session(engine) as session:
        with pytest.raises(
            importer.CanonicalElementMissingError,
            match="atomic_number=1",
        ):
            importer.import_pubchem_elements(
                session,
                adapter=_adapter(FIRST_RETRIEVAL),
                atomic_numbers={1},
            )
        session.rollback()

        assert _count(session, "element") == 0
        assert session.scalar(select(func.count()).select_from(tables["element_source"])) == 0


def test_pubchem_import_accepts_only_known_english_spelling_variants() -> None:
    importer = _load_importer()
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine, Session(engine) as session:
        bootstrap_element_identities(session)
        aluminium_id = session.scalar(
            select(tables["element"].c.id).where(tables["element"].c.atomic_number == 13)
        )
        result = importer.import_pubchem_elements(
            session,
            adapter=_identity_adapter(13, "Al", "Aluminum"),
            atomic_numbers={13},
        )
        session.commit()

        assert result.element_ids == (ElementId(aluminium_id),)
        assert (
            session.scalar(
                select(tables["element"].c.name_en).where(tables["element"].c.id == aluminium_id)
            )
            == "aluminium"
        )

        with pytest.raises(importer.CanonicalElementIdentityMismatchError):
            importer.import_pubchem_elements(
                session,
                adapter=_identity_adapter(13, "Ai", "Aluminum"),
                atomic_numbers={13},
            )
        session.rollback()

        with pytest.raises(importer.CanonicalElementIdentityMismatchError):
            importer.import_pubchem_elements(
                session,
                adapter=_identity_adapter(14, "Si", "Silicone"),
                atomic_numbers={14},
            )
