"""M05 application model linking M01 Reaction identity to equation facts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from chem_wiki.modules.chemistry_core import (
    Condition,
    IonId,
    Phase,
    ProvenanceRef,
    Reaction,
    ReactionCode,
    ReactionId,
    ReactionParticipant,
    ReactionParticipantId,
    ReactionRole,
    ReactionStatus,
    StoichiometricCoefficient,
    SubstanceId,
)

from .equation import EquationError, EquationMode, balance_equation

ParticipantTargetType = Literal["substance", "ion"]
ConservationState = Literal["balanced", "unbalanced", "invalid"]


@dataclass(frozen=True, slots=True)
class ParticipantCommand:
    id: UUID
    target_type: ParticipantTargetType
    target_id: UUID
    role: ReactionRole
    stoichiometry: Decimal
    phase: str | None = None


@dataclass(frozen=True, slots=True)
class PhenomenonFact:
    id: UUID
    name: str
    category: str
    description: str
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.category.strip() or not self.description.strip():
            raise ValueError("现象名称、类别和描述不能为空")


@dataclass(frozen=True, slots=True)
class ReviewedRedoxMetadata:
    oxidized_species: str
    reduced_species: str
    electron_count: int
    explanation: str

    def __post_init__(self) -> None:
        if self.electron_count <= 0:
            raise ValueError("氧化还原电子数必须为正整数")
        if not all(
            value.strip()
            for value in (self.oxidized_species, self.reduced_species, self.explanation)
        ):
            raise ValueError("氧化还原审核元数据不能为空")


@dataclass(frozen=True, slots=True)
class CreateReactionCommand:
    id: UUID
    reaction_code: str
    equation_text: str
    equation_mode: EquationMode
    reaction_type: str
    participants: tuple[ParticipantCommand, ...]
    conditions: tuple[Condition, ...] = ()
    reversible: bool = False
    exam_heat: Decimal = Decimal(0)
    status: ReactionStatus = ReactionStatus.DRAFT
    provenance: tuple[ProvenanceRef, ...] = ()
    phenomena: tuple[PhenomenonFact, ...] = ()
    redox_metadata: ReviewedRedoxMetadata | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReactionDocument:
    reaction: Reaction
    equation_text: str
    equation_mode: EquationMode
    reaction_type: str
    exam_heat: Decimal
    conservation_state: ConservationState
    phenomena: tuple[PhenomenonFact, ...]
    redox_metadata: ReviewedRedoxMetadata | None
    reviewed_by: str | None
    reviewed_at: datetime | None


def _build_participant(command: ParticipantCommand) -> ReactionParticipant:
    target = (
        SubstanceId(command.target_id)
        if command.target_type == "substance"
        else IonId(command.target_id)
    )
    return ReactionParticipant(
        id=ReactionParticipantId(command.id),
        target=target,
        role=command.role,
        stoichiometry=StoichiometricCoefficient(command.stoichiometry),
        phase=Phase(command.phase) if command.phase else None,
    )


def _validate_publication(
    command: CreateReactionCommand,
    *,
    conservation_state: ConservationState,
    balanced_coefficients: tuple[int, ...] | None,
) -> None:
    if command.status is not ReactionStatus.PUBLISHED:
        return
    if conservation_state != "balanced" or balanced_coefficients is None:
        raise ValueError("发布反应必须通过元素与适用时的电荷守恒")
    if not command.provenance:
        raise ValueError("发布反应必须具有经审核来源")
    if not command.reviewed_by or command.reviewed_at is None:
        raise ValueError("发布反应必须记录审核人和审核时间")
    equation_participants = tuple(
        item
        for role in (ReactionRole.REACTANT, ReactionRole.PRODUCT)
        for item in command.participants
        if item.role is role
    )
    expected = tuple(Decimal(value) for value in balanced_coefficients)
    actual = tuple(item.stoichiometry for item in equation_participants)
    if actual != expected:
        raise ValueError("参与物系数必须与已配平方程式一致")
    if any(not phenomenon.provenance for phenomenon in command.phenomena):
        raise ValueError("发布的现象事实必须具有经审核来源")


def prepare_reaction(command: CreateReactionCommand) -> ReactionDocument:
    """Validate a write command and construct the canonical M05 document."""

    reaction_type = command.reaction_type.strip()
    if not reaction_type:
        raise ValueError("反应类型不能为空")
    if not Decimal(0) <= command.exam_heat <= Decimal(1):
        raise ValueError("exam_heat 必须在 0 到 1 之间")

    participants = tuple(_build_participant(item) for item in command.participants)
    reaction = Reaction(
        id=ReactionId(command.id),
        code=ReactionCode(command.reaction_code),
        participants=participants,
        conditions=command.conditions,
        status=command.status,
        reversible=command.reversible,
        provenance=command.provenance,
    )

    balanced_coefficients: tuple[int, ...] | None = None
    equation_text = command.equation_text.strip()
    try:
        result = balance_equation(equation_text, mode=command.equation_mode)
        if result.state == "balanced":
            balanced_coefficients = result.coefficients
            conservation_state: ConservationState = (
                "balanced" if result.input_state == "balanced" else "unbalanced"
            )
            if command.status is ReactionStatus.PUBLISHED:
                conservation_state = "balanced"
                equation_text = result.formatted_equation
        else:
            conservation_state = "invalid"
    except EquationError:
        conservation_state = "invalid"

    _validate_publication(
        command,
        conservation_state="balanced" if balanced_coefficients is not None else conservation_state,
        balanced_coefficients=balanced_coefficients,
    )
    return ReactionDocument(
        reaction=reaction,
        equation_text=equation_text,
        equation_mode=command.equation_mode,
        reaction_type=reaction_type,
        exam_heat=command.exam_heat,
        conservation_state=conservation_state,
        phenomena=command.phenomena,
        redox_metadata=command.redox_metadata,
        reviewed_by=command.reviewed_by.strip() if command.reviewed_by else None,
        reviewed_at=command.reviewed_at,
    )
