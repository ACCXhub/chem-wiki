from importlib import import_module
from uuid import UUID

from fastapi.testclient import TestClient

ELEMENT_ID = UUID("12345678-1234-5678-1234-567812345678")


def _page():
    wiki = import_module("chem_wiki.modules.element_wiki.read_model")
    periodic = import_module("chem_wiki.modules.periodic_table.read_model")
    element = periodic.build_periodic_table(
        [
            periodic.CanonicalElementSnapshot(
                id=ELEMENT_ID,
                atomic_number=17,
                symbol="Cl",
                name_zh="氯",
                name_en="chlorine",
                electronegativity=None,
                electronegativity_scale=None,
                first_ionization_energy=None,
                first_ionization_energy_unit=None,
            )
        ]
    )[0]
    return wiki.build_element_wiki(
        element,
        wiki.CanonicalElementWikiSnapshot(
            atomic_weight_value=None,
            atomic_weight_lower=None,
            atomic_weight_upper=None,
            atomic_weight_uncertainty=None,
            electronegativity_value=None,
            electronegativity_scale=None,
            first_ionization_energy_value=None,
            first_ionization_energy_unit=None,
            atomic_radius_value=None,
            atomic_radius_unit=None,
            atomic_radius_qualifier=None,
            published_sources=(),
        ),
    )


class StubReader:
    def get_element(self, element_id: UUID):
        return _page() if element_id == ELEMENT_ID else None


def test_element_wiki_endpoint_uses_stable_uuid_and_does_not_leak_m02_storage_schema() -> None:
    api = import_module("chem_wiki.modules.element_wiki.api")
    main = import_module("chem_wiki.main")
    application = main.create_app()
    application.dependency_overrides[api.get_element_wiki_reader] = lambda: StubReader()

    response = TestClient(application).get(f"/v1/elements/{ELEMENT_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["identity"] == {
        "id": str(ELEMENT_ID),
        "atomicNumber": 17,
        "symbol": "Cl",
        "nameZh": "氯",
        "nameEn": "chlorine",
        "status": "confirmed",
    }
    assert payload["classification"] == {
        "category": "halogen",
        "period": 3,
        "group": 17,
        "block": "p",
    }
    assert payload["graph"]["nodes"][0]["type"] == "Element"
    assert payload["graph"]["edges"] == []
    serialized = response.text
    assert "rawPayload" not in serialized
    assert "claimId" not in serialized
    assert "selectionReason" not in serialized


def test_element_wiki_endpoint_returns_404_for_unknown_uuid() -> None:
    api = import_module("chem_wiki.modules.element_wiki.api")
    main = import_module("chem_wiki.main")
    application = main.create_app()
    application.dependency_overrides[api.get_element_wiki_reader] = lambda: StubReader()

    response = TestClient(application).get(f"/v1/elements/{UUID(int=99)}")

    assert response.status_code == 404
    assert response.json() == {"detail": "未找到该元素"}
