from dataclasses import dataclass

from .identifiers import StructureId, SubstanceId
from .provenance import ProvenanceRef


@dataclass(frozen=True, slots=True)
class StructureFormat:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            raise ValueError("structure format must not be blank")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class StructureText:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("structure text must not be blank")


@dataclass(frozen=True, slots=True)
class Structure:
    id: StructureId
    substance_id: SubstanceId
    format: StructureFormat
    text: StructureText
    provenance: tuple[ProvenanceRef, ...] = ()
