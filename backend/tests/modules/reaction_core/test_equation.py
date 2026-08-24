import pytest

from chem_wiki.modules.reaction_core import (
    EquationError,
    EquationMode,
    balance_equation,
)


def test_balances_molecular_equation_with_smallest_integer_coefficients() -> None:
    result = balance_equation("H2 + O2 -> H2O")

    assert result.state == "balanced"
    assert result.coefficients == (2, 1, 2)
    assert result.formatted_equation == "2H₂ + O₂ → 2H₂O"
    assert [(item.element, item.reactants, item.products) for item in result.elements] == [
        ("H", 4, 4),
        ("O", 2, 2),
    ]
    assert result.charge is None


def test_balances_parenthesized_formula_using_exact_arithmetic() -> None:
    result = balance_equation("Al + H2SO4 -> Al2(SO4)3 + H2")

    assert result.coefficients == (2, 3, 1, 3)
    assert all(item.conserved for item in result.elements)


def test_validates_charge_and_keeps_phase_in_ionic_display() -> None:
    result = balance_equation(
        "Ag+(aq) + Cl-(aq) -> AgCl(s)",
        mode=EquationMode.NET_IONIC,
    )

    assert result.coefficients == (1, 1, 1)
    assert result.charge is not None
    assert (result.charge.reactants, result.charge.products, result.charge.conserved) == (
        0,
        0,
        True,
    )
    assert result.phenomenon == "生成白色氯化银沉淀"
    assert result.formatted_equation == "Ag⁺(aq) + Cl⁻(aq) → AgCl(s)↓"


def test_reports_approved_no_net_ionic_case_without_fabricating_product() -> None:
    result = balance_equation(
        "Na+(aq) + NO3-(aq)",
        mode=EquationMode.NET_IONIC,
    )

    assert result.state == "no_net_ionic"
    assert result.products == ()
    assert result.message == "普通水溶液中无净离子反应"


def test_reports_unbalanced_input_but_returns_balanced_equation() -> None:
    result = balance_equation("H2 + O2 -> 2H2O")

    assert result.input_state == "unbalanced"
    assert result.coefficients == (2, 1, 2)


@pytest.mark.parametrize(
    ("equation", "code"),
    [
        ("H2 -> H2O", "no_solution"),
        ("Mg(OH -> MgO + H2O", "invalid_formula"),
        ("H2 + O2", "missing_arrow"),
    ],
)
def test_rejects_invalid_or_unsolvable_equations(equation: str, code: str) -> None:
    with pytest.raises(EquationError) as error:
        balance_equation(equation)

    assert error.value.code == code
    assert error.value.state == "invalid"
