from importlib import import_module

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql.schema import MetaData

FROZEN_TABLES = {
    "element",
    "element_property",
    "element_source",
    "element_source_record",
    "element_claim",
    "element_published_value",
}


def _metadata() -> MetaData:
    try:
        module = import_module("chem_wiki.modules.element_data")
    except ModuleNotFoundError as exc:
        pytest.fail(f"M02 persistence module is missing: {exc}")
    return module.ElementDataBase.metadata


def _unique_column_sets(table_name: str) -> set[tuple[str, ...]]:
    table = _metadata().tables[table_name]
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _check_names(table_name: str) -> set[str | None]:
    table = _metadata().tables[table_name]
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_metadata_contains_only_the_six_frozen_m02_tables() -> None:
    assert set(_metadata().tables) == FROZEN_TABLES


def test_element_uses_uuid_primary_key_and_atomic_number_natural_key() -> None:
    table = _metadata().tables["element"]

    assert [column.name for column in table.primary_key.columns] == ["id"]
    assert isinstance(table.c.id.type, UUID)
    assert table.c.atomic_number.primary_key is False
    assert ("atomic_number",) in _unique_column_sets("element")
    assert "ck_element_atomic_number_1_118" in _check_names("element")
    assert table.c.name_en.nullable is False


def test_canonical_tables_keep_raw_and_source_specific_fields_out() -> None:
    element = _metadata().tables["element"]
    element_property = _metadata().tables["element_property"]
    source_record = _metadata().tables["element_source_record"]

    assert set(element.c.keys()) == {"id", "atomic_number", "symbol", "name_zh", "name_en"}
    assert "source_id" not in element.c
    assert "raw_payload" not in element.c
    assert "raw_payload" not in element_property.c
    assert isinstance(source_record.c.raw_payload.type, JSONB)


def test_source_records_and_claims_have_idempotency_keys() -> None:
    assert (
        "source_id",
        "source_version",
        "record_key",
        "content_sha256",
    ) in _unique_column_sets("element_source_record")
    assert (
        "source_record_id",
        "field_name",
        "transform_version",
    ) in _unique_column_sets("element_claim")
    assert "ck_element_source_record_content_sha256" in _check_names("element_source_record")


def test_published_value_has_field_level_provenance_foreign_key_chain() -> None:
    published = _metadata().tables["element_published_value"]
    claim = _metadata().tables["element_claim"]
    source_record = _metadata().tables["element_source_record"]

    assert [column.name for column in published.primary_key.columns] == [
        "element_id",
        "field_name",
    ]

    published_foreign_keys = [
        constraint
        for constraint in published.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert any(
        tuple(element.parent.name for element in constraint.elements)
        == ("claim_id", "element_id", "field_name")
        and tuple(element.target_fullname for element in constraint.elements)
        == (
            "element_claim.id",
            "element_claim.element_id",
            "element_claim.field_name",
        )
        for constraint in published_foreign_keys
    )
    assert any(foreign_key.column.table is source_record for foreign_key in claim.foreign_keys)
    assert any(
        foreign_key.column.table.name == "element_source"
        for foreign_key in source_record.foreign_keys
    )


def test_known_element_properties_use_relational_columns() -> None:
    table = _metadata().tables["element_property"]

    assert set(table.c.keys()) == {
        "element_id",
        "atomic_weight_value",
        "atomic_weight_lower",
        "atomic_weight_upper",
        "atomic_weight_uncertainty",
        "group_no",
        "period_no",
        "block",
        "electronegativity_value",
        "electronegativity_scale",
        "first_ionization_energy_value",
        "first_ionization_energy_unit",
        "atomic_radius_value",
        "atomic_radius_unit",
        "atomic_radius_qualifier",
    }
    assert "ck_element_property_atomic_weight_shape" in _check_names("element_property")
    assert "ck_element_property_electronegativity_pair" in _check_names("element_property")
    assert "ck_element_property_ionization_energy_pair" in _check_names("element_property")
    assert "ck_element_property_atomic_radius_group" in _check_names("element_property")
