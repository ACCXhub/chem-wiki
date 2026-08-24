from datetime import UTC, datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

FIXTURE = Path(__file__).parents[2] / "fixtures" / "nist_asd_ionization_h_he.csv"
RETRIEVED_AT = datetime(2026, 8, 20, 14, 30, tzinfo=UTC)


def _load_module() -> Any:
    try:
        return import_module("chem_wiki.modules.element_data.nist_asd")
    except ModuleNotFoundError as exc:
        pytest.fail(f"NIST ASD adapter is missing: {exc}")


def _adapter(nist_asd: Any) -> Any:
    def fetch_text(url: str, timeout: float) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        assert parsed.scheme == "https"
        assert parsed.netloc == "physics.nist.gov"
        assert parsed.path == "/cgi-bin/ASD/ie.pl"
        assert query["spectra"] == ["H I;He I"]
        assert query["units"] == ["1"]
        assert query["format"] == ["2"]
        assert query["ion_charge_out"] == ["on"]
        assert query["e_out"] == ["0"]
        assert query["unc_out"] == ["on"]
        assert query["biblio"] == ["on"]
        assert "output" not in query
        assert "conf_out" not in query
        assert "shells_out" not in query
        assert timeout == 30.0
        return FIXTURE.read_text(encoding="utf-8")

    return nist_asd.NistAsdAdapter(fetch_text=fetch_text, clock=lambda: RETRIEVED_AT)


def test_adapter_preserves_nist_value_uncertainty_qualifier_and_reference() -> None:
    nist_asd = _load_module()

    records = _adapter(nist_asd).fetch_neutral_atoms({"He", "H"})

    assert [record.record_key for record in records] == ["H I", "He I"]
    hydrogen = records[0]
    assert hydrogen.atomic_number == 1
    assert hydrogen.symbol == "H"
    assert hydrogen.source_version == "nist-asd-5.12"
    assert hydrogen.retrieved_at == RETRIEVED_AT
    assert hydrogen.raw_value == "13.598434599702"
    assert hydrogen.value_ev == Decimal("13.598434599702")
    assert hydrogen.uncertainty_ev == Decimal("0.000000000012")
    assert hydrogen.qualifier == "()"
    assert hydrogen.raw_payload["References"] == "HDEL"
    assert hydrogen.raw_payload["ASD Citation"] == nist_asd.NIST_ASD_CITATION
    assert len(hydrogen.content_sha256) == 64
    assert set(hydrogen.content_sha256) <= set("0123456789abcdef")

    helium = records[1]
    assert helium.atomic_number == 2
    assert helium.symbol == "He"
    assert helium.value_ev == Decimal("24.587389011")
    assert helium.uncertainty_ev == Decimal("0.000000025")
    assert helium.qualifier is None
    assert helium.raw_payload["References"] == "L17714"


def test_adapter_emits_only_the_existing_canonical_ionization_claim() -> None:
    nist_asd = _load_module()
    record = _adapter(nist_asd).fetch_neutral_atoms({"H", "He"})[0]

    claim = _adapter(nist_asd).normalize(record)

    assert claim.field_name == "first_ionization_energy"
    assert claim.raw_value == "13.598434599702"
    assert claim.normalized_numeric == Decimal("13.598434599702")
    assert claim.canonical_unit == "eV"
    assert claim.uncertainty == Decimal("0.000000000012")
    assert claim.qualifier == "()"


def test_adapter_rejects_ionic_rows_in_the_neutral_atom_slice() -> None:
    nist_asd = _load_module()
    ionic_fixture = FIXTURE.read_text(encoding="utf-8").replace(
        '"=""0""","=""Hydrogen"""',
        '"=""1""","=""Hydrogen"""',
        1,
    )
    adapter = nist_asd.NistAsdAdapter(
        fetch_text=lambda _url, _timeout: ionic_fixture,
        clock=lambda: RETRIEVED_AT,
    )

    with pytest.raises(nist_asd.NistAsdPayloadError, match="neutral atom"):
        adapter.fetch_neutral_atoms({"H", "He"})
