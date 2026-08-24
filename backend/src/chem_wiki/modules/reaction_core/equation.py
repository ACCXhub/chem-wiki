"""Exact equation parsing, balancing and conservation for M05."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from functools import reduce
from math import gcd, lcm


class EquationMode(StrEnum):
    MOLECULAR = "molecular"
    IONIC = "ionic"
    NET_IONIC = "net_ionic"


class EquationError(ValueError):
    state = "invalid"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class EquationSpecies:
    formula: str
    composition: tuple[tuple[str, int], ...]
    charge: int
    phase: str | None
    input_coefficient: Fraction


@dataclass(frozen=True, slots=True)
class ElementConservation:
    element: str
    reactants: int
    products: int
    conserved: bool


@dataclass(frozen=True, slots=True)
class ChargeConservation:
    reactants: int
    products: int
    conserved: bool


@dataclass(frozen=True, slots=True)
class EquationBalance:
    state: str
    input_state: str
    mode: EquationMode
    reactants: tuple[EquationSpecies, ...]
    products: tuple[EquationSpecies, ...]
    coefficients: tuple[int, ...]
    formatted_equation: str
    elements: tuple[ElementConservation, ...]
    charge: ChargeConservation | None
    message: str | None = None
    phenomenon: str | None = None


_ARROW_PATTERN = re.compile(r"\s*(?:->|→|=)\s*")
_TERM_SEPARATOR = re.compile(r"\s+\+\s+")
_PHASE_PATTERN = re.compile(r"\((aq|s|l|g)\)$", re.IGNORECASE)
_CARET_CHARGE_PATTERN = re.compile(r"\^(\d*)([+-])$")
_SIMPLE_CHARGE_PATTERN = re.compile(r"([+-])$")
_COEFFICIENT_PATTERN = re.compile(r"^(?:(\d+)(?:/(\d+))?\s*)?(.+)$")
_SUBSCRIPT_TRANSLATION = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUPERSCRIPT_TRANSLATION = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def _formula_composition(formula: str) -> dict[str, int]:
    index = 0

    def number() -> int:
        nonlocal index
        start = index
        while index < len(formula) and formula[index].isdigit():
            index += 1
        if start == index:
            return 1
        value = int(formula[start:index])
        if value <= 0:
            raise EquationError("invalid_formula", "化学式下标必须为正整数")
        return value

    def group(*, nested: bool) -> dict[str, int]:
        nonlocal index
        result: dict[str, int] = {}
        found = False
        while index < len(formula):
            character = formula[index]
            if character == ")":
                if not nested:
                    raise EquationError("invalid_formula", "化学式括号不匹配")
                break
            if character == "(":
                index += 1
                child = group(nested=True)
                if index >= len(formula) or formula[index] != ")":
                    raise EquationError("invalid_formula", "化学式括号不匹配")
                index += 1
                multiplier = number()
                for element, count in child.items():
                    result[element] = result.get(element, 0) + count * multiplier
                found = True
                continue
            if not character.isupper() or not character.isascii():
                raise EquationError("invalid_formula", f"无法识别化学式：{formula}")
            start = index
            index += 1
            while index < len(formula) and formula[index].islower() and formula[index].isascii():
                index += 1
            element = formula[start:index]
            result[element] = result.get(element, 0) + number()
            found = True
        if not found:
            raise EquationError("invalid_formula", f"无法识别化学式：{formula}")
        return result

    composition = group(nested=False)
    if index != len(formula):
        raise EquationError("invalid_formula", "化学式括号不匹配")
    return composition


def _parse_species(term: str) -> EquationSpecies:
    match = _COEFFICIENT_PATTERN.fullmatch(term.strip())
    if match is None:
        raise EquationError("invalid_term", f"无法识别方程式项：{term}")
    numerator, denominator, body = match.groups()
    if numerator is None:
        coefficient = Fraction(1)
    else:
        denominator_value = int(denominator) if denominator else 1
        if denominator_value == 0:
            raise EquationError("invalid_coefficient", "化学计量系数分母不能为零")
        coefficient = Fraction(int(numerator), denominator_value)
        if coefficient <= 0:
            raise EquationError("invalid_coefficient", "化学计量系数必须为正")

    phase_match = _PHASE_PATTERN.search(body)
    phase = phase_match.group(1).lower() if phase_match else None
    if phase_match:
        body = body[: phase_match.start()]

    charge = 0
    charge_match = _CARET_CHARGE_PATTERN.search(body)
    if charge_match:
        magnitude = int(charge_match.group(1) or "1")
        charge = magnitude if charge_match.group(2) == "+" else -magnitude
        body = body[: charge_match.start()]
    else:
        charge_match = _SIMPLE_CHARGE_PATTERN.search(body)
        if charge_match:
            charge = 1 if charge_match.group(1) == "+" else -1
            body = body[: charge_match.start()]

    formula = body.strip()
    if not formula:
        raise EquationError("invalid_formula", "化学式不能为空")
    composition = _formula_composition(formula)
    return EquationSpecies(
        formula=formula,
        composition=tuple(sorted(composition.items())),
        charge=charge,
        phase=phase,
        input_coefficient=coefficient,
    )


def _parse_side(side: str) -> tuple[EquationSpecies, ...]:
    terms = _TERM_SEPARATOR.split(side.strip()) if side.strip() else []
    if not terms or any(not term.strip() for term in terms):
        raise EquationError("missing_participant", "方程式两侧都必须包含化学式")
    return tuple(_parse_species(term) for term in terms)


def _nullspace_vector(matrix: list[list[Fraction]]) -> tuple[Fraction, ...]:
    if not matrix or not matrix[0]:
        raise EquationError("no_solution", "方程式没有可配平的守恒关系")
    rows = [row[:] for row in matrix]
    row_count = len(rows)
    column_count = len(rows[0])
    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(column_count):
        selected = next(
            (row for row in range(pivot_row, row_count) if rows[row][column] != 0),
            None,
        )
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        divisor = rows[pivot_row][column]
        rows[pivot_row] = [value / divisor for value in rows[pivot_row]]
        for row in range(row_count):
            if row == pivot_row or rows[row][column] == 0:
                continue
            factor = rows[row][column]
            rows[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(rows[row], rows[pivot_row], strict=True)
            ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == row_count:
            break

    free_columns = [column for column in range(column_count) if column not in pivot_columns]
    if len(free_columns) != 1:
        code = "no_solution" if not free_columns else "ambiguous_solution"
        message = "方程式没有非零守恒解" if not free_columns else "方程式存在多组独立解，请补充物种"
        raise EquationError(code, message)
    free = free_columns[0]
    vector = [Fraction(0) for _ in range(column_count)]
    vector[free] = Fraction(1)
    for row, pivot in reversed(list(enumerate(pivot_columns))):
        vector[pivot] = -sum(
            rows[row][column] * vector[column] for column in range(pivot + 1, column_count)
        )
    return tuple(vector)


def _smallest_positive_integers(vector: tuple[Fraction, ...]) -> tuple[int, ...]:
    denominator_lcm = reduce(lcm, (value.denominator for value in vector), 1)
    integers = [int(value * denominator_lcm) for value in vector]
    if integers and all(value < 0 for value in integers):
        integers = [-value for value in integers]
    if not integers or any(value <= 0 for value in integers):
        raise EquationError("no_positive_solution", "无法得到全部为正的化学计量系数")
    common = reduce(gcd, integers)
    return tuple(value // common for value in integers)


def _display_species(species: EquationSpecies, coefficient: int, *, precipitate: bool) -> str:
    prefix = "" if coefficient == 1 else str(coefficient)
    formula = species.formula.translate(_SUBSCRIPT_TRANSLATION)
    if species.charge:
        magnitude = abs(species.charge)
        charge = ("" if magnitude == 1 else str(magnitude)) + ("+" if species.charge > 0 else "-")
        formula += charge.translate(_SUPERSCRIPT_TRANSLATION)
    phase = f"({species.phase})" if species.phase else ""
    return f"{prefix}{formula}{phase}{'↓' if precipitate else ''}"


def _is_silver_chloride_case(
    reactants: tuple[EquationSpecies, ...], products: tuple[EquationSpecies, ...]
) -> bool:
    reactant_keys = {(item.formula, item.charge) for item in reactants}
    return reactant_keys == {("Ag", 1), ("Cl", -1)} and [
        (item.formula, item.charge) for item in products
    ] == [("AgCl", 0)]


def _no_net_ionic_result(equation: str, mode: EquationMode) -> EquationBalance | None:
    if mode is not EquationMode.NET_IONIC or _ARROW_PATTERN.search(equation):
        return None
    reactants = _parse_side(equation)
    keys = {(item.formula, item.charge) for item in reactants}
    if keys != {("Na", 1), ("NO3", -1)} or len(reactants) != 2:
        return None
    display = " + ".join(_display_species(item, 1, precipitate=False) for item in reactants)
    return EquationBalance(
        state="no_net_ionic",
        input_state="not_applicable",
        mode=mode,
        reactants=reactants,
        products=(),
        coefficients=(1, 1),
        formatted_equation=f"{display}（无净离子反应）",
        elements=(),
        charge=None,
        message="普通水溶液中无净离子反应",
    )


def balance_equation(
    equation: str, *, mode: EquationMode = EquationMode.MOLECULAR
) -> EquationBalance:
    """Balance one equation using an exact rational nullspace calculation."""

    equation = equation.strip()
    if not equation:
        raise EquationError("empty_equation", "请输入化学方程式")
    no_reaction = _no_net_ionic_result(equation, mode)
    if no_reaction is not None:
        return no_reaction

    parts = _ARROW_PATTERN.split(equation)
    if len(parts) != 2:
        raise EquationError("missing_arrow", "方程式必须包含一个反应箭头")
    reactants = _parse_side(parts[0])
    products = _parse_side(parts[1])
    species = reactants + products
    elements = sorted({element for item in species for element, _ in item.composition})
    include_charge = any(item.charge for item in species)
    matrix: list[list[Fraction]] = []
    for element in elements:
        matrix.append(
            [
                Fraction(
                    dict(item.composition).get(element, 0) * (1 if index < len(reactants) else -1)
                )
                for index, item in enumerate(species)
            ]
        )
    if include_charge:
        matrix.append(
            [
                Fraction(item.charge * (1 if index < len(reactants) else -1))
                for index, item in enumerate(species)
            ]
        )

    coefficients = _smallest_positive_integers(_nullspace_vector(matrix))
    split = len(reactants)
    element_results = tuple(
        ElementConservation(
            element=element,
            reactants=sum(
                coefficients[index] * dict(item.composition).get(element, 0)
                for index, item in enumerate(reactants)
            ),
            products=sum(
                coefficients[split + index] * dict(item.composition).get(element, 0)
                for index, item in enumerate(products)
            ),
            conserved=True,
        )
        for element in elements
    )
    charge_result = None
    if include_charge:
        reactant_charge = sum(
            coefficients[index] * item.charge for index, item in enumerate(reactants)
        )
        product_charge = sum(
            coefficients[split + index] * item.charge for index, item in enumerate(products)
        )
        charge_result = ChargeConservation(
            reactants=reactant_charge,
            products=product_charge,
            conserved=reactant_charge == product_charge,
        )

    input_values = tuple(item.input_coefficient for item in species)
    input_conserved = all(
        sum(matrix[row][column] * input_values[column] for column in range(len(species))) == 0
        for row in range(len(matrix))
    )
    silver_chloride = _is_silver_chloride_case(reactants, products)
    left = " + ".join(
        _display_species(item, coefficients[index], precipitate=False)
        for index, item in enumerate(reactants)
    )
    right = " + ".join(
        _display_species(
            item,
            coefficients[split + index],
            precipitate=silver_chloride and item.formula == "AgCl",
        )
        for index, item in enumerate(products)
    )
    return EquationBalance(
        state="balanced",
        input_state="balanced" if input_conserved else "unbalanced",
        mode=mode,
        reactants=reactants,
        products=products,
        coefficients=coefficients,
        formatted_equation=f"{left} → {right}",
        elements=element_results,
        charge=charge_result,
        phenomenon="生成白色氯化银沉淀" if silver_chloride else None,
    )
