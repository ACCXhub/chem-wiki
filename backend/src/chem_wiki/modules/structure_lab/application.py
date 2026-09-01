"""Library-neutral M06 structure analysis contracts."""

from dataclasses import dataclass
from typing import Literal, Protocol

from chem_wiki.modules.chemistry_core import FunctionalGroupId, StructureId

StructureInputFormat = Literal["smiles", "molblock"]
AnalysisState = Literal["valid", "invalid", "unsupported"]


@dataclass(frozen=True, slots=True)
class StructureInput:
    format: str
    text: str


@dataclass(frozen=True, slots=True)
class StructureDescriptors:
    molecular_weight: float
    exact_mass: float
    heavy_atom_count: int
    hydrogen_bond_donors: int
    hydrogen_bond_acceptors: int
    rotatable_bond_count: int
    formal_charge: int


@dataclass(frozen=True, slots=True)
class AtomCoordinate:
    atom_index: int
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class StructureDepiction:
    svg: str
    width: int
    height: int
    atom_coordinates: tuple[AtomCoordinate, ...]
    format: Literal["svg"] = "svg"


@dataclass(frozen=True, slots=True)
class StructureConformer:
    state: Literal["available", "unavailable"]
    mol_block: str | None = None
    reason: str | None = None
    format: Literal["mol"] = "mol"


@dataclass(frozen=True, slots=True)
class FunctionalGroupOccurrence:
    atom_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DetectedFunctionalGroup:
    functional_group_id: FunctionalGroupId
    key: str
    name_zh: str
    name_en: str
    smarts: str
    pattern_source: str
    occurrences: tuple[FunctionalGroupOccurrence, ...]


@dataclass(frozen=True, slots=True)
class StructuralTeachingFact:
    """One structure-derived fact for learner-facing presentation."""

    key: str
    atom_indices: tuple[int, ...]
    value: float | None = None


@dataclass(frozen=True, slots=True)
class StructuralTeachingProjection:
    """A bounded hierarchy of structural evidence, independent of catalog identity."""

    primary: StructuralTeachingFact | None
    observations: tuple[StructuralTeachingFact, ...]


@dataclass(frozen=True, slots=True)
class StructureAnalysis:
    state: AnalysisState
    input_format: str
    structure_id: StructureId | None = None
    canonical_smiles: str | None = None
    formula: str | None = None
    descriptors: StructureDescriptors | None = None
    depiction: StructureDepiction | None = None
    conformer: StructureConformer | None = None
    functional_groups: tuple[DetectedFunctionalGroup, ...] = ()
    structural_teaching: StructuralTeachingProjection | None = None
    code: str | None = None
    message: str | None = None


class ChemistryEngine(Protocol):
    def analyze(self, structure: StructureInput) -> StructureAnalysis: ...


def analyze_structure(
    *,
    input_format: str,
    text: str,
    engine: ChemistryEngine,
) -> StructureAnalysis:
    """Interpret one structure through an engine hidden behind the M06 port."""

    return engine.analyze(StructureInput(format=input_format.strip().lower(), text=text))
