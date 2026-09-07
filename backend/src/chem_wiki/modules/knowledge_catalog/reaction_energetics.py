"""Derived standard reaction enthalpy over catalog Reaction and thermochemistry facts."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from .read_model import (
    CatalogReactionEnthalpyContribution,
    CatalogReactionEnthalpyMissingParticipant,
    CatalogReactionParticipantResult,
    CatalogReactionResult,
    CatalogSourceAttributionResult,
    CatalogStandardReactionEnthalpy,
)

MissingReason = Literal[
    "unresolved_species",
    "phase_unavailable",
    "invalid_stoichiometry",
    "formation_enthalpy_unavailable",
    "reference_conditions_unavailable",
]


@dataclass(frozen=True, slots=True)
class PhaseFormationEnthalpy:
    species_id: str
    phase: str
    temperature_k: Decimal
    standard_pressure_bar: Decimal
    delta_f_h_kj_mol: Decimal | None
    sources: tuple[CatalogSourceAttributionResult, ...] = ()


def _coefficient(value: float | str) -> Decimal | None:
    try:
        coefficient = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return coefficient if coefficient.is_finite() and coefficient > 0 else None


def _missing(
    participant: CatalogReactionParticipantResult,
    reason: MissingReason,
) -> CatalogReactionEnthalpyMissingParticipant:
    return CatalogReactionEnthalpyMissingParticipant(
        role=participant.role,
        name_zh=participant.name_zh,
        formula=participant.formula,
        phase=participant.phase,
        reason=reason,
    )


def _unavailable(
    missing: list[CatalogReactionEnthalpyMissingParticipant],
) -> CatalogStandardReactionEnthalpy:
    return CatalogStandardReactionEnthalpy(
        status="unavailable",
        value_kj_mol=None,
        classification=None,
        reference_temperature_k=None,
        standard_pressure_bar=None,
        missing_participants=missing,
    )


def derive_standard_reaction_enthalpy(
    reaction: CatalogReactionResult,
    records: list[PhaseFormationEnthalpy],
) -> CatalogStandardReactionEnthalpy:
    """Apply Hess's law using exact participant species, phase and shared conditions."""

    records_by_key: dict[tuple[str, str], list[PhaseFormationEnthalpy]] = {}
    for record in records:
        records_by_key.setdefault((record.species_id, record.phase), []).append(record)

    participant_records: list[
        tuple[CatalogReactionParticipantResult, Decimal, list[PhaseFormationEnthalpy]]
    ] = []
    missing: list[CatalogReactionEnthalpyMissingParticipant] = []
    for participant in reaction.participants:
        coefficient = _coefficient(participant.coefficient)
        if coefficient is None or participant.role not in {"reactant", "product"}:
            missing.append(_missing(participant, "invalid_stoichiometry"))
            continue
        if participant.species_id is None:
            missing.append(_missing(participant, "unresolved_species"))
            continue
        if participant.phase is None:
            missing.append(_missing(participant, "phase_unavailable"))
            continue
        matches = [
            record
            for record in records_by_key.get((participant.species_id, participant.phase), [])
            if record.delta_f_h_kj_mol is not None
        ]
        if not matches:
            missing.append(_missing(participant, "formation_enthalpy_unavailable"))
            continue
        participant_records.append((participant, coefficient, matches))

    if missing:
        return _unavailable(missing)

    common_conditions: set[tuple[Decimal, Decimal]] | None = None
    for _, _, matches in participant_records:
        conditions = {(record.temperature_k, record.standard_pressure_bar) for record in matches}
        common_conditions = (
            conditions if common_conditions is None else common_conditions & conditions
        )
    if not common_conditions:
        return _unavailable(
            [
                _missing(participant, "reference_conditions_unavailable")
                for participant, _, _ in participant_records
            ]
        )

    temperature_k, standard_pressure_bar = min(common_conditions)
    contributions: list[CatalogReactionEnthalpyContribution] = []
    for participant, coefficient, matches in participant_records:
        record = next(
            item
            for item in matches
            if (item.temperature_k, item.standard_pressure_bar)
            == (temperature_k, standard_pressure_bar)
        )
        delta_f_h = record.delta_f_h_kj_mol
        assert delta_f_h is not None
        signed = coefficient * delta_f_h * (1 if participant.role == "product" else -1)
        contributions.append(
            CatalogReactionEnthalpyContribution(
                role=participant.role,
                name_zh=participant.name_zh,
                formula=participant.formula,
                phase=participant.phase,
                coefficient=coefficient,
                delta_f_h_kj_mol=delta_f_h,
                signed_contribution_kj_mol=signed,
                sources=list(record.sources),
            )
        )

    value = sum(
        (item.signed_contribution_kj_mol for item in contributions),
        start=Decimal(0),
    )
    classification = "exothermic" if value < 0 else "endothermic" if value > 0 else "thermoneutral"
    return CatalogStandardReactionEnthalpy(
        status="complete",
        value_kj_mol=value,
        classification=classification,
        reference_temperature_k=temperature_k,
        standard_pressure_bar=standard_pressure_bar,
        contributions=contributions,
    )
