from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .identifiers import IonId, ReactionId, ReactionParticipantId, SubstanceId
from .provenance import ProvenanceRef


class ReactionStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ReactionRole(StrEnum):
    REACTANT = "reactant"
    PRODUCT = "product"
    CATALYST = "catalyst"
    SOLVENT = "solvent"


type ParticipantTarget = SubstanceId | IonId


@dataclass(frozen=True, slots=True)
class ReactionCode:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            raise ValueError("reaction code must not be blank")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class StoichiometricCoefficient:
    value: Decimal

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("stoichiometry must be positive")


@dataclass(frozen=True, slots=True)
class Phase:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            raise ValueError("phase must not be blank")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class Condition:
    kind: str
    value: str | Decimal | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        kind = self.kind.strip()
        if not kind:
            raise ValueError("condition kind must not be blank")
        if isinstance(self.value, str) and not self.value.strip():
            raise ValueError("condition value must not be blank")
        if self.unit is not None and not self.unit.strip():
            raise ValueError("condition unit must not be blank")
        object.__setattr__(self, "kind", kind)


@dataclass(frozen=True, slots=True)
class ReactionParticipant:
    id: ReactionParticipantId
    target: ParticipantTarget
    role: ReactionRole
    stoichiometry: StoichiometricCoefficient
    phase: Phase | None = None
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.target, (SubstanceId, IonId)):
            raise TypeError("target must be SubstanceId or IonId")


@dataclass(frozen=True, slots=True)
class Reaction:
    id: ReactionId
    code: ReactionCode
    participants: tuple[ReactionParticipant, ...]
    conditions: tuple[Condition, ...] = ()
    status: ReactionStatus = ReactionStatus.DRAFT
    reversible: bool = False
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        participant_ids = [participant.id for participant in self.participants]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("participant id must be unique within a reaction")

        roles = {participant.role for participant in self.participants}
        if ReactionRole.REACTANT not in roles:
            raise ValueError("reaction requires at least one reactant")
        if ReactionRole.PRODUCT not in roles:
            raise ValueError("reaction requires at least one product")
