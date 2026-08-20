from dataclasses import dataclass

from .composition import ChemicalFormula, CompositionEntry
from .identifiers import SubstanceId
from .provenance import ProvenanceRef


@dataclass(frozen=True, slots=True)
class Substance:
    id: SubstanceId
    formula: ChemicalFormula
    composition: tuple[CompositionEntry, ...]
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        if not self.composition:
            raise ValueError("substance composition must not be empty")
