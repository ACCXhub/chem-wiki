from fastapi.testclient import TestClient

from chem_wiki.main import create_app


def test_analyze_smiles_returns_normalized_structure_and_viewer_data() -> None:
    response = TestClient(create_app()).post(
        "/v1/structures/analyze",
        json={"format": "smiles", "text": " CCO "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "valid"
    assert payload["structureId"]
    assert payload["inputFormat"] == "smiles"
    assert payload["canonicalSmiles"] == "CCO"
    assert payload["formula"] == "C2H6O"
    assert payload["descriptors"] == {
        "molecularWeight": 46.069,
        "exactMass": 46.0419,
        "heavyAtomCount": 3,
        "hydrogenBondDonors": 1,
        "hydrogenBondAcceptors": 1,
        "rotatableBondCount": 0,
        "formalCharge": 0,
    }
    assert payload["depiction"]["format"] == "svg"
    assert payload["depiction"]["width"] == 600
    assert payload["depiction"]["height"] == 420
    assert payload["depiction"]["svg"].startswith("<?xml")
    assert {item["atomIndex"] for item in payload["depiction"]["atomCoordinates"]} == {
        0,
        1,
        2,
    }
    assert payload["conformer"]["state"] == "available"
    assert payload["conformer"]["format"] == "mol"
    assert "V2000" in payload["conformer"]["molBlock"]
    assert [group["key"] for group in payload["functionalGroups"]] == ["alcohol"]
    assert payload["functionalGroups"][0]["nameZh"] == "醇羟基"
    assert payload["functionalGroups"][0]["occurrences"] == [{"atomIndices": [2]}]
    assert payload["message"] is None


def test_invalid_valence_returns_an_explicit_non_publishable_state() -> None:
    response = TestClient(create_app()).post(
        "/v1/structures/analyze",
        json={"format": "smiles", "text": "C(C)(C)(C)(C)C"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "state": "invalid",
        "inputFormat": "smiles",
        "structureId": None,
        "canonicalSmiles": None,
        "formula": None,
        "descriptors": None,
        "depiction": None,
        "conformer": None,
        "functionalGroups": [],
        "code": "invalid_structure",
        "message": "无法解析该结构，或原子价态不合法",
    }


def test_unsupported_representation_is_distinct_from_invalid_chemistry() -> None:
    response = TestClient(create_app()).post(
        "/v1/structures/analyze",
        json={"format": "inchi", "text": "InChI=1S/CH4/h1H4"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "unsupported"
    assert response.json()["code"] == "unsupported_format"
    assert response.json()["message"] == "当前仅支持 SMILES 与 molfile 结构输入"


def test_multiple_functional_groups_keep_stable_catalog_identity_and_atom_matches() -> None:
    client = TestClient(create_app())
    first = client.post(
        "/v1/structures/analyze",
        json={"format": "smiles", "text": "NCC(=O)O"},
    ).json()
    second = client.post(
        "/v1/structures/analyze",
        json={"format": "smiles", "text": "NCC(=O)O"},
    ).json()

    groups = {group["key"]: group for group in first["functionalGroups"]}
    assert set(groups) == {"amine", "carboxylic_acid"}
    assert groups["amine"]["occurrences"] == [{"atomIndices": [0]}]
    assert groups["carboxylic_acid"]["occurrences"] == [{"atomIndices": [2, 3, 4]}]
    assert {group["key"]: group["functionalGroupId"] for group in first["functionalGroups"]} == {
        group["key"]: group["functionalGroupId"] for group in second["functionalGroups"]
    }
    assert first["structureId"] != second["structureId"]


def test_analyze_accepts_a_molfile_without_exposing_rdkit_objects() -> None:
    mol_block = """acetic acid
  ChemWiki

  4  3  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    1.5000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  2  3  1  0  0  0  0
  2  4  2  0  0  0  0
M  END
"""

    response = TestClient(create_app()).post(
        "/v1/structures/analyze",
        json={"format": "molblock", "text": mol_block},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "valid"
    assert payload["inputFormat"] == "molblock"
    assert payload["canonicalSmiles"] == "CC(=O)O"
    assert payload["formula"] == "C2H4O2"
    assert [item["key"] for item in payload["functionalGroups"]] == ["carboxylic_acid"]
