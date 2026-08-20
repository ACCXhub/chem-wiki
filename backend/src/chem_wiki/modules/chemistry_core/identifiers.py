from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ElementId:
    value: UUID


@dataclass(frozen=True, slots=True)
class IonId:
    value: UUID


@dataclass(frozen=True, slots=True)
class SubstanceId:
    value: UUID


@dataclass(frozen=True, slots=True)
class StructureId:
    value: UUID


@dataclass(frozen=True, slots=True)
class FunctionalGroupId:
    value: UUID


@dataclass(frozen=True, slots=True)
class ReactionId:
    value: UUID


@dataclass(frozen=True, slots=True)
class ReactionParticipantId:
    value: UUID
