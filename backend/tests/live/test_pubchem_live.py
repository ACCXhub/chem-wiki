import os

import pytest

from chem_wiki.modules.element_data.pubchem import PubChemAdapter, PubChemRequestError

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("CHEM_WIKI_RUN_LIVE_PUBCHEM") != "1",
        reason="set CHEM_WIKI_RUN_LIVE_PUBCHEM=1 to call the official PubChem service",
    ),
]


def test_live_pubchem_periodic_table_returns_hydrogen_and_helium() -> None:
    try:
        records = PubChemAdapter().fetch_elements({1, 2})
    except PubChemRequestError as exc:
        if exc.status_code == 503:
            pytest.skip("PubChem returned its documented transient HTTP 503 throttling response")
        raise

    assert [record.raw_payload["AtomicNumber"] for record in records] == ["1", "2"]
    assert [record.raw_payload["Symbol"] for record in records] == ["H", "He"]
    assert [record.raw_payload["Name"] for record in records] == ["Hydrogen", "Helium"]
    assert records[0].raw_payload["IonizationEnergy"]
    assert records[1].raw_payload["AtomicRadius"]
