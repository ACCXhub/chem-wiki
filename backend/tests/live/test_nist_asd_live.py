import os
from decimal import Decimal

import pytest

from chem_wiki.modules.element_data.nist_asd import NistAsdAdapter, NistAsdRequestError

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("CHEM_WIKI_RUN_LIVE_NIST") != "1",
        reason="set CHEM_WIKI_RUN_LIVE_NIST=1 to call the official NIST ASD service",
    ),
]


def test_live_nist_asd_returns_neutral_hydrogen_and_helium_ionization_energies() -> None:
    try:
        records = NistAsdAdapter().fetch_neutral_atoms({"H", "He"})
    except NistAsdRequestError as exc:
        if exc.status_code in {429, 503}:
            pytest.skip(f"NIST ASD returned transient HTTP {exc.status_code}")
        raise

    assert [(record.atomic_number, record.symbol) for record in records] == [(1, "H"), (2, "He")]
    assert records[0].value_ev > Decimal(13)
    assert records[1].value_ev > Decimal(24)
    assert records[0].uncertainty_ev is not None
    assert records[0].raw_payload["References"]
    assert records[0].source_version == "nist-asd-5.12"
