from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, inspect, select
from sqlalchemy.exc import DBAPIError, IntegrityError

from chem_wiki.config import Settings
from chem_wiki.modules.chemistry_core import ElementId
from chem_wiki.modules.element_data import ElementDataBase

BACKEND_ROOT = Path(__file__).parents[2]
FROZEN_TABLES = {
    "element",
    "element_property",
    "element_source",
    "element_source_record",
    "element_claim",
    "element_published_value",
}


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
        remaining_tables = set(inspect(engine).get_table_names())
        engine.dispose()
        assert FROZEN_TABLES.isdisjoint(remaining_tables)


def _insert_published_hydrogen(connection: Connection) -> dict[str, Any]:
    tables = ElementDataBase.metadata.tables
    element_id = ElementId(uuid4())
    source_id = uuid4()
    source_record_id = uuid4()
    retrieved_at = datetime(2026, 8, 20, tzinfo=UTC)

    connection.execute(
        tables["element_source"]
        .insert()
        .values(
            id=source_id,
            source_key="test-source",
            title="Test source",
            source_type="standard",
            reuse_policy="allowed",
        )
    )
    connection.execute(
        tables["element_source_record"]
        .insert()
        .values(
            id=source_record_id,
            source_id=source_id,
            source_version="2026-08",
            record_key="H",
            source_url="https://example.test/elements/H",
            retrieved_at=retrieved_at,
            content_sha256="a" * 64,
            raw_payload={"atomic_number": 1, "symbol": "H"},
        )
    )
    connection.execute(
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
    claim_ids: dict[str, object] = {}
    for field_name, values in claim_values.items():
        claim_id = uuid4()
        claim_ids[field_name] = claim_id
        connection.execute(
            tables["element_claim"]
            .insert()
            .values(
                id=claim_id,
                element_id=element_id.value,
                source_record_id=source_record_id,
                field_name=field_name,
                verification_status="verified",
                transform_version="v1",
                **values,
            )
        )
        connection.execute(
            tables["element_published_value"]
            .insert()
            .values(
                element_id=element_id.value,
                field_name=field_name,
                claim_id=claim_id,
                selection_method="authority_policy",
                policy_version="v1",
                selected_by="policy:v1",
                selection_reason="authoritative calibration",
                selected_at=retrieved_at,
            )
        )

    return {
        "element_id": element_id,
        "source_id": source_id,
        "source_record_id": source_record_id,
        "claim_ids": claim_ids,
    }


def _insert_published_group_one(connection: Connection, inserted: dict[str, Any]) -> None:
    tables = ElementDataBase.metadata.tables
    group_claim_id = uuid4()
    connection.execute(
        tables["element_property"]
        .insert()
        .values(
            element_id=inserted["element_id"].value,
            group_no=1,
        )
    )
    connection.execute(
        tables["element_claim"]
        .insert()
        .values(
            id=group_claim_id,
            element_id=inserted["element_id"].value,
            source_record_id=inserted["source_record_id"],
            field_name="group_no",
            raw_value="1",
            normalized_integer=1,
            verification_status="verified",
            transform_version="v1",
        )
    )
    connection.execute(
        tables["element_published_value"]
        .insert()
        .values(
            element_id=inserted["element_id"].value,
            field_name="group_no",
            claim_id=group_claim_id,
            selection_method="authority_policy",
            policy_version="v1",
            selected_by="policy:v1",
            selection_reason="authoritative calibration",
            selected_at=datetime(2026, 8, 20, tzinfo=UTC),
        )
    )


@pytest.mark.integration
def test_migration_round_trip_enforces_natural_and_idempotency_keys() -> None:
    element = ElementDataBase.metadata.tables["element"]
    source_record = ElementDataBase.metadata.tables["element_source_record"]

    with _migrated_engine() as engine:
        assert FROZEN_TABLES <= set(inspect(engine).get_table_names())

        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)
            element_id = inserted["element_id"]
            assert (
                connection.scalar(select(element.c.id).where(element.c.atomic_number == 1))
                == element_id.value
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                element.insert().values(
                    id=uuid4(),
                    atomic_number=1,
                    symbol="X",
                    name_zh="重复",
                    name_en="duplicate",
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                element.insert().values(
                    id=uuid4(),
                    atomic_number=0,
                    symbol="Z",
                    name_zh="越界",
                    name_en="out-of-range",
                )
            )

        source_record_values = {
            "source_id": inserted["source_id"],
            "source_version": "2026-08",
            "record_key": "H",
            "source_url": "https://example.test/elements/H",
            "retrieved_at": datetime(2026, 8, 20, tzinfo=UTC),
            "content_sha256": "a" * 64,
            "raw_payload": {"symbol": "H"},
        }
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(source_record.insert().values(id=uuid4(), **source_record_values))


@pytest.mark.integration
def test_canonical_values_require_matching_published_claims_at_commit() -> None:
    element = ElementDataBase.metadata.tables["element"]

    with _migrated_engine() as engine, pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(
            element.insert().values(
                id=uuid4(),
                atomic_number=2,
                symbol="He",
                name_zh="氦",
                name_en="helium",
            )
        )


@pytest.mark.integration
def test_canonical_updates_must_match_the_selected_claim() -> None:
    element = ElementDataBase.metadata.tables["element"]

    with _migrated_engine() as engine:
        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                element.update()
                .where(element.c.id == inserted["element_id"].value)
                .values(symbol="X")
            )


@pytest.mark.integration
def test_source_records_and_claims_are_immutable_evidence() -> None:
    source_record = ElementDataBase.metadata.tables["element_source_record"]
    claim = ElementDataBase.metadata.tables["element_claim"]

    with _migrated_engine() as engine:
        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                source_record.update()
                .where(source_record.c.id == inserted["source_record_id"])
                .values(source_url="https://example.test/changed")
            )

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                claim.update()
                .where(claim.c.id == inserted["claim_ids"]["symbol"])
                .values(raw_value="changed")
            )


@pytest.mark.integration
def test_element_identity_and_source_key_are_immutable() -> None:
    element = ElementDataBase.metadata.tables["element"]
    source = ElementDataBase.metadata.tables["element_source"]

    with _migrated_engine() as engine:
        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                element.update()
                .where(element.c.id == inserted["element_id"].value)
                .values(atomic_number=2)
            )

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                source.update()
                .where(source.c.id == inserted["source_id"])
                .values(source_key="renamed-source")
            )


@pytest.mark.integration
def test_prohibited_sources_cannot_retain_raw_payloads() -> None:
    source = ElementDataBase.metadata.tables["element_source"]
    source_record = ElementDataBase.metadata.tables["element_source_record"]

    with _migrated_engine() as engine:
        source_id = uuid4()
        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                source.insert().values(
                    id=source_id,
                    source_key="prohibited-source",
                    title="Prohibited source",
                    source_type="open_source",
                    reuse_policy="prohibited",
                )
            )
            connection.execute(
                source_record.insert().values(
                    id=uuid4(),
                    source_id=source_id,
                    source_version="v1",
                    record_key="H",
                    retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
                    content_sha256="b" * 64,
                    raw_payload={"symbol": "H"},
                )
            )

        with engine.begin() as connection:
            allowed_source_id = uuid4()
            connection.execute(
                source.insert().values(
                    id=allowed_source_id,
                    source_key="allowed-then-prohibited",
                    title="Mutable policy source",
                    source_type="database",
                    reuse_policy="allowed",
                )
            )
            connection.execute(
                source_record.insert().values(
                    id=uuid4(),
                    source_id=allowed_source_id,
                    source_version="v1",
                    record_key="He",
                    retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
                    content_sha256="c" * 64,
                    raw_payload={"symbol": "He"},
                )
            )

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                source.update()
                .where(source.c.id == allowed_source_id)
                .values(reuse_policy="prohibited")
            )


@pytest.mark.integration
def test_source_record_hash_must_be_lowercase_sha256() -> None:
    source = ElementDataBase.metadata.tables["element_source"]
    source_record = ElementDataBase.metadata.tables["element_source_record"]

    with _migrated_engine() as engine:
        source_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                source.insert().values(
                    id=source_id,
                    source_key="hash-source",
                    title="Hash source",
                    source_type="standard",
                    reuse_policy="allowed",
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                source_record.insert().values(
                    id=uuid4(),
                    source_id=source_id,
                    source_version="v1",
                    record_key="H",
                    retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
                    content_sha256="not-a-sha256",
                    raw_payload=None,
                )
            )


@pytest.mark.integration
def test_canonical_property_and_selection_can_be_removed_together() -> None:
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine:
        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)
            _insert_published_group_one(connection, inserted)

        with engine.begin() as connection:
            connection.execute(
                tables["element_property"]
                .update()
                .where(tables["element_property"].c.element_id == inserted["element_id"].value)
                .values(group_no=None)
            )
            connection.execute(
                tables["element_published_value"]
                .delete()
                .where(
                    tables["element_published_value"].c.element_id == inserted["element_id"].value,
                    tables["element_published_value"].c.field_name == "group_no",
                )
            )


@pytest.mark.integration
def test_removing_only_one_side_of_a_published_property_is_rejected() -> None:
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine:
        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)
            _insert_published_group_one(connection, inserted)

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                tables["element_published_value"]
                .delete()
                .where(
                    tables["element_published_value"].c.element_id == inserted["element_id"].value,
                    tables["element_published_value"].c.field_name == "group_no",
                )
            )

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                tables["element_property"]
                .update()
                .where(tables["element_property"].c.element_id == inserted["element_id"].value)
                .values(group_no=None)
            )


@pytest.mark.integration
def test_ionization_publication_integrity_uses_canonical_column_precision() -> None:
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine:
        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)
            claim_id = uuid4()
            connection.execute(
                tables["element_property"]
                .insert()
                .values(
                    element_id=inserted["element_id"].value,
                    first_ionization_energy_value=Decimal("13.598434599702"),
                    first_ionization_energy_unit="eV",
                )
            )
            connection.execute(
                tables["element_claim"]
                .insert()
                .values(
                    id=claim_id,
                    element_id=inserted["element_id"].value,
                    source_record_id=inserted["source_record_id"],
                    field_name="first_ionization_energy",
                    raw_value="13.598434599702",
                    normalized_numeric=Decimal("13.598434599702"),
                    canonical_unit="eV",
                    uncertainty=Decimal("0.000000000012"),
                    qualifier="()",
                    verification_status="verified",
                    transform_version="nist-v1",
                )
            )
            connection.execute(
                tables["element_published_value"]
                .insert()
                .values(
                    element_id=inserted["element_id"].value,
                    field_name="first_ionization_energy",
                    claim_id=claim_id,
                    selection_method="authority_policy",
                    policy_version="nist-v1",
                    selected_by="policy:nist-v1",
                    selection_reason="NIST precision calibration",
                    selected_at=datetime(2026, 8, 20, tzinfo=UTC),
                )
            )

        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(
                tables["element_property"]
                .update()
                .where(tables["element_property"].c.element_id == inserted["element_id"].value)
                .values(first_ionization_energy_value=Decimal("13.597"))
            )


@pytest.mark.integration
def test_database_enforces_property_claim_and_publication_checks() -> None:
    tables = ElementDataBase.metadata.tables

    with _migrated_engine() as engine:
        with engine.begin() as connection:
            inserted = _insert_published_hydrogen(connection)

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_property"]
                .insert()
                .values(
                    element_id=inserted["element_id"].value,
                    group_no=19,
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_property"]
                .insert()
                .values(
                    element_id=inserted["element_id"].value,
                    electronegativity_value="2.200",
                )
            )

        claim_base = {
            "element_id": inserted["element_id"].value,
            "source_record_id": inserted["source_record_id"],
            "raw_value": "invalid",
        }
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_claim"]
                .insert()
                .values(
                    id=uuid4(),
                    field_name="pinyin",
                    normalized_text="qing",
                    verification_status="verified",
                    transform_version="invalid-field",
                    **claim_base,
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_claim"]
                .insert()
                .values(
                    id=uuid4(),
                    field_name="group_no",
                    normalized_text="1",
                    normalized_integer=1,
                    verification_status="verified",
                    transform_version="invalid-shape",
                    **claim_base,
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_claim"]
                .insert()
                .values(
                    id=uuid4(),
                    field_name="group_no",
                    normalized_integer=1,
                    verification_status="approved",
                    transform_version="invalid-status",
                    **claim_base,
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_claim"]
                .insert()
                .values(
                    id=uuid4(),
                    field_name="symbol",
                    normalized_text="H",
                    verification_status="verified",
                    transform_version="v1",
                    **claim_base,
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_published_value"]
                .update()
                .where(
                    tables["element_published_value"].c.element_id == inserted["element_id"].value,
                    tables["element_published_value"].c.field_name == "symbol",
                )
                .values(selection_method="automatic")
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                tables["element_published_value"]
                .update()
                .where(
                    tables["element_published_value"].c.element_id == inserted["element_id"].value,
                    tables["element_published_value"].c.field_name == "symbol",
                )
                .values(claim_id=inserted["claim_ids"]["name_en"])
            )

        group_claim_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                tables["element_property"]
                .insert()
                .values(
                    element_id=inserted["element_id"].value,
                    group_no=1,
                )
            )
            connection.execute(
                tables["element_claim"]
                .insert()
                .values(
                    id=group_claim_id,
                    field_name="group_no",
                    normalized_integer=1,
                    verification_status="verified",
                    transform_version="v1",
                    **claim_base,
                )
            )
            connection.execute(
                tables["element_published_value"]
                .insert()
                .values(
                    element_id=inserted["element_id"].value,
                    field_name="group_no",
                    claim_id=group_claim_id,
                    selection_method="authority_policy",
                    policy_version="v1",
                    selected_by="policy:v1",
                    selection_reason="authoritative calibration",
                    selected_at=datetime(2026, 8, 20, tzinfo=UTC),
                )
            )
