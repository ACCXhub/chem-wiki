import re
from dataclasses import dataclass

from .identifiers import ElementId
from .provenance import ProvenanceRef


@dataclass(frozen=True, slots=True)
class AtomicNumber:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("atomic number must be positive")


@dataclass(frozen=True, slots=True)
class ElementSymbol:
    value: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Z][a-z]{0,2}", self.value) is None:
            raise ValueError("element symbol is invalid")


@dataclass(frozen=True, slots=True)
class Element:
    id: ElementId
    atomic_number: AtomicNumber
    symbol: ElementSymbol
    name_zh: str
    name_en: str
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        name_zh = self.name_zh.strip()
        if not name_zh:
            raise ValueError("name_zh must not be blank")

        name_en = self.name_en.strip()
        if not name_en:
            raise ValueError("name_en must not be blank")

        object.__setattr__(self, "name_zh", name_zh)
        object.__setattr__(self, "name_en", name_en)
