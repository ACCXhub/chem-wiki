from dataclasses import dataclass

from .composition import ChemicalFormula, CompositionEntry
from .identifiers import IonId
from .provenance import ProvenanceRef


@dataclass(frozen=True, slots=True)
class ElectricCharge:
    value: int

    def __post_init__(self) -> None:
        if self.value == 0:
            raise ValueError("ion charge must be nonzero")


@dataclass(frozen=True, slots=True)
class Ion:
    id: IonId
    formula: ChemicalFormula
    composition: tuple[CompositionEntry, ...]
    charge: ElectricCharge
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        if not self.composition:
            raise ValueError("ion composition must not be empty")
