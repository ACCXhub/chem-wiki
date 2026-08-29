from datetime import UTC, datetime
from decimal import Decimal
from importlib import import_module
from typing import Any

import pytest

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
            },
            {
                "Cell": [
                    "2",
                    "He",
                    "Helium",
                    "4.00260",
                    "D9FFFF",
                    "1s2",
                    "",
                    "140",
                    "24.587",
                    "",
                    "0",
                    "Gas",
                    "0.95",
                    "4.22",
                    "0.0001785",
                    "Noble gas",
                    "Ancient",
                ]
            },
        ],
    }
}

RETRIEVED_AT = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)


def _load_module() -> Any:
    try:
        return import_module("chem_wiki.modules.element_data.pubchem")
    except ModuleNotFoundError as exc:
        pytest.fail(f"PubChem ETL module is missing: {exc}")


def _adapter(pubchem: Any) -> Any:
    def fetch_json(url: str, timeout: float) -> dict[str, Any]:
        if url != "https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON":
            raise AssertionError(f"unexpected PubChem URL: {url}")
        if timeout != 30.0:
            raise AssertionError(f"unexpected timeout: {timeout}")
        return PUBCHEM_PAYLOAD

    return pubchem.PubChemAdapter(fetch_json=fetch_json, clock=lambda: RETRIEVED_AT)


def _claims_by_field(normalized: Any) -> dict[str, Any]:
    return {claim.field_name: claim for claim in normalized.claims}


def test_adapter_filters_requested_elements_and_keeps_complete_source_rows() -> None:
    pubchem = _load_module()

    records = _adapter(pubchem).fetch_elements({2})

    assert len(records) == 1
    record = records[0]
    assert record.record_key == "2"
    assert record.source_version == "pug-periodictable-json-v1"
    assert record.source_url == "https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON"
    assert record.retrieved_at == RETRIEVED_AT
    assert record.raw_payload == dict(
        zip(PUBCHEM_COLUMNS, PUBCHEM_PAYLOAD["Table"]["Row"][1]["Cell"])
    )
    assert len(record.content_sha256) == 64
    assert set(record.content_sha256) <= set("0123456789abcdef")
    assert _adapter(pubchem).fetch_elements({2})[0].content_sha256 == record.content_sha256


def test_normalizer_emits_validated_identity_and_pubchem_property_claims() -> None:
    pubchem = _load_module()
    record = _adapter(pubchem).fetch_elements({1})[0]

    normalized = _adapter(pubchem).normalize(record)
    claims = _claims_by_field(normalized)

    assert normalized.atomic_number == 1
    assert normalized.symbol == "H"
    assert normalized.name_en == "hydrogen"
    assert claims["atomic_number"].normalized_integer == 1
    assert claims["symbol"].normalized_text == "H"
    assert claims["name_en"].raw_value == "Hydrogen"
    assert claims["name_en"].normalized_text == "hydrogen"
    assert claims["electronegativity"].normalized_numeric == Decimal("2.2")
    assert claims["electronegativity"].qualifier == "Pauling"
    assert claims["first_ionization_energy"].normalized_numeric == Decimal("13.598")
    assert claims["first_ionization_energy"].canonical_unit == "eV"
    assert claims["atomic_radius"].normalized_numeric == Decimal(120)
    assert claims["atomic_radius"].canonical_unit == "pm"
    assert claims["atomic_radius"].qualifier == "atomic"
    assert normalized.publishable_fields == frozenset(
        {"electronegativity", "first_ionization_energy", "atomic_radius"}
    )
    assert {"atomic_number", "symbol", "name_en"}.isdisjoint(normalized.publishable_fields)


def test_adapter_owns_normalization_of_its_source_specific_record() -> None:
    pubchem = _load_module()
    adapter = _adapter(pubchem)

    normalized = adapter.normalize(adapter.fetch_elements({1})[0])
    claims = _claims_by_field(normalized)

    assert normalized.atomic_number == 1
    assert normalized.symbol == "H"
    assert normalized.name_en == "hydrogen"
    assert claims["first_ionization_energy"].normalized_numeric == Decimal("13.598")


def test_normalizer_omits_missing_optional_pubchem_claims() -> None:
    pubchem = _load_module()
    record = _adapter(pubchem).fetch_elements({2})[0]

    claims = _claims_by_field(_adapter(pubchem).normalize(record))

    assert "electronegativity" not in claims
    assert claims["atomic_radius"].normalized_numeric == Decimal(140)
    assert claims["first_ionization_energy"].normalized_numeric == Decimal("24.587")


def test_adapter_rejects_rows_that_do_not_match_the_official_column_schema() -> None:
    pubchem = _load_module()
    malformed_payload = {
        "Table": {
            "Columns": {"Column": PUBCHEM_COLUMNS},
            "Row": [{"Cell": ["1", "H"]}],
        }
    }

    adapter = pubchem.PubChemAdapter(
        fetch_json=lambda _url, _timeout: malformed_payload,
        clock=lambda: RETRIEVED_AT,
    )

    with pytest.raises(pubchem.PubChemPayloadError, match="column count"):
        adapter.fetch_elements({1})


def test_versioned_snapshot_adapter_validates_and_selects_real_elements() -> None:
    pubchem = _load_module()

    records = pubchem.PubChemSnapshotAdapter().fetch_elements({1, 6, 8, 17, 26})
    normalized = [pubchem.PubChemSnapshotAdapter.normalize(record) for record in records]

    assert [item.symbol for item in normalized] == ["H", "C", "O", "Cl", "Fe"]
    assert all(
        any(claim.field_name == "first_ionization_energy" for claim in item.claims)
        for item in normalized
    )
    assert (
        pubchem.PubChemSnapshotAdapter.normalize(
            pubchem.PubChemSnapshotAdapter().fetch_elements({13})[0]
        ).name_en
        == "aluminum"
    )


def test_normalizer_rejects_invalid_m01_identity_values() -> None:
    pubchem = _load_module()
    valid = _adapter(pubchem).fetch_elements({1})[0]
    invalid = pubchem.PubChemRawRecord(
        record_key="0",
        source_version=valid.source_version,
        source_url=valid.source_url,
        retrieved_at=valid.retrieved_at,
        content_sha256=valid.content_sha256,
        raw_payload={**valid.raw_payload, "AtomicNumber": "0", "Symbol": "hydrogen"},
    )

    with pytest.raises(pubchem.ElementNormalizationError, match="PubChem element identity"):
        _adapter(pubchem).normalize(invalid)
