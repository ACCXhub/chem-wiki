from dataclasses import dataclass
from decimal import Decimal

from .identifiers import ElementId
from .provenance import ProvenanceRef


@dataclass(frozen=True, slots=True)
class ChemicalFormula:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            raise ValueError("formula must not be blank")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class CompositionEntry:
    element_id: ElementId
    amount: Decimal
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("composition amount must be positive")
