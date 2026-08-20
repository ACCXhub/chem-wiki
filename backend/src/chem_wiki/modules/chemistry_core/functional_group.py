from dataclasses import dataclass

from .identifiers import FunctionalGroupId
from .provenance import ProvenanceRef


@dataclass(frozen=True, slots=True)
class FunctionalGroup:
    id: FunctionalGroupId
    name: str
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("functional group name must not be blank")
        object.__setattr__(self, "name", name)
