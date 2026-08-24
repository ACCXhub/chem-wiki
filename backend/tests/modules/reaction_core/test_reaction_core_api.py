from fastapi.testclient import TestClient

from chem_wiki.main import create_app


def test_balance_endpoint_returns_display_dto_and_conservation_evidence() -> None:
    response = TestClient(create_app()).post(
        "/v1/reactions/balance",
        json={"equation": "H2 + O2 -> H2O", "mode": "molecular"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "state": "balanced",
        "inputState": "unbalanced",
        "mode": "molecular",
        "formattedEquation": "2H₂ + O₂ → 2H₂O",
        "coefficients": [2, 1, 2],
        "reactants": [
            {"formula": "H2", "coefficient": 2, "phase": None, "charge": 0},
            {"formula": "O2", "coefficient": 1, "phase": None, "charge": 0},
        ],
        "products": [
            {"formula": "H2O", "coefficient": 2, "phase": None, "charge": 0},
        ],
        "conservation": {
            "elements": [
                {"element": "H", "reactants": 4, "products": 4, "conserved": True},
                {"element": "O", "reactants": 2, "products": 2, "conserved": True},
            ],
            "charge": None,
        },
        "message": None,
        "phenomenon": None,
        "redox": {
            "state": "not_inferred",
            "message": "氧化还原解释仅接受经审核元数据，不由配平方程式推断",
        },
    }


def test_balance_endpoint_returns_explicit_invalid_state() -> None:
    response = TestClient(create_app()).post(
        "/v1/reactions/balance",
        json={"equation": "H2 -> H2O", "mode": "molecular"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "state": "invalid",
            "code": "no_solution",
            "message": "方程式没有非零守恒解",
        }
    }


def test_balance_endpoint_supports_frozen_no_net_ionic_example() -> None:
    response = TestClient(create_app()).post(
        "/v1/reactions/balance",
        json={"equation": "Na+(aq) + NO3-(aq)", "mode": "net_ionic"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "no_net_ionic"
    assert payload["products"] == []
    assert payload["message"] == "普通水溶液中无净离子反应"
