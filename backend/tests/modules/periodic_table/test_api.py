from importlib import import_module
from uuid import UUID

from fastapi.testclient import TestClient


class StubReader:
    def list_elements(self):
        read_model = import_module("chem_wiki.modules.periodic_table.read_model")
        return read_model.build_periodic_table(
            [
                read_model.CanonicalElementSnapshot(
                    id=UUID(int=1),
                    atomic_number=1,
                    symbol="H",
                    name_zh="氢",
                    name_en="hydrogen",
                    electronegativity=2.2,
                    electronegativity_scale="Pauling",
                    first_ionization_energy=13.598,
                    first_ionization_energy_unit="eV",
                )
            ]
        )


def test_elements_endpoint_returns_stable_source_neutral_contract() -> None:
    api = import_module("chem_wiki.modules.periodic_table.api")
    main = import_module("chem_wiki.main")
    application = main.create_app()
    application.dependency_overrides[api.get_periodic_table_reader] = lambda: StubReader()

    response = TestClient(application).get("/v1/elements")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "atomicNumber": 1,
            "symbol": "H",
            "nameZh": "氢",
            "nameEn": "hydrogen",
            "category": "reactive-nonmetal",
            "status": "confirmed",
            "layout": {
                "period": 1,
                "group": 1,
                "row": 1,
                "column": 1,
                "block": "s",
            },
            "properties": {
                "electronegativity": {"value": 2.2, "unit": "Pauling"},
                "firstIonizationEnergy": {"value": 13.598, "unit": "eV"},
            },
        }
    ]
