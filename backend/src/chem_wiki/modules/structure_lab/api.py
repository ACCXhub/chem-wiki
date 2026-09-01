"""HTTP boundary for M06 Structure Lab."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from .application import StructureAnalysis, analyze_structure
from .rdkit_adapter import RdkitChemistryEngine


class AnalyzeStructureRequest(BaseModel):
    format: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1, max_length=200_000)


class StructureDescriptorsDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    molecular_weight: float = Field(alias="molecularWeight")
    exact_mass: float = Field(alias="exactMass")
    heavy_atom_count: int = Field(alias="heavyAtomCount")
    hydrogen_bond_donors: int = Field(alias="hydrogenBondDonors")
    hydrogen_bond_acceptors: int = Field(alias="hydrogenBondAcceptors")
    rotatable_bond_count: int = Field(alias="rotatableBondCount")
    formal_charge: int = Field(alias="formalCharge")


class AtomCoordinateDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    atom_index: int = Field(alias="atomIndex")
    x: float
    y: float


class StructureDepictionDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    format: Literal["svg"] = "svg"
    svg: str
    width: int
    height: int
    atom_coordinates: list[AtomCoordinateDto] = Field(alias="atomCoordinates")


class StructureConformerDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    state: Literal["available", "unavailable"]
    format: Literal["mol"] = "mol"
    mol_block: str | None = Field(default=None, alias="molBlock")
    reason: str | None = None


class FunctionalGroupOccurrenceDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    atom_indices: list[int] = Field(alias="atomIndices")


class FunctionalGroupDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    functional_group_id: UUID = Field(alias="functionalGroupId")
    key: str
    name_zh: str = Field(alias="nameZh")
    name_en: str = Field(alias="nameEn")
    smarts: str
    pattern_source: str = Field(alias="patternSource")
    occurrences: list[FunctionalGroupOccurrenceDto]


class StructuralTeachingFactDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    atom_indices: list[int] = Field(alias="atomIndices")
    value: float | None = None


class StructuralTeachingProjectionDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    primary: StructuralTeachingFactDto | None = None
    observations: list[StructuralTeachingFactDto]


class AnalyzeStructureResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    state: Literal["valid", "invalid", "unsupported"]
    input_format: str = Field(alias="inputFormat")
    structure_id: UUID | None = Field(default=None, alias="structureId")
    canonical_smiles: str | None = Field(default=None, alias="canonicalSmiles")
    formula: str | None = None
    descriptors: StructureDescriptorsDto | None = None
    depiction: StructureDepictionDto | None = None
    conformer: StructureConformerDto | None = None
    functional_groups: list[FunctionalGroupDto] = Field(
        default_factory=list,
        alias="functionalGroups",
    )
    structural_teaching: StructuralTeachingProjectionDto | None = Field(
        default=None,
        alias="structuralTeaching",
    )
    code: str | None = None
    message: str | None = None


def _to_response(result: StructureAnalysis) -> AnalyzeStructureResponse:
    return AnalyzeStructureResponse.model_validate(
        {
            "state": result.state,
            "input_format": result.input_format,
            "structure_id": result.structure_id.value if result.structure_id else None,
            "canonical_smiles": result.canonical_smiles,
            "formula": result.formula,
            "descriptors": result.descriptors,
            "depiction": result.depiction,
            "conformer": result.conformer,
            "functional_groups": [
                {
                    "functional_group_id": item.functional_group_id.value,
                    "key": item.key,
                    "name_zh": item.name_zh,
                    "name_en": item.name_en,
                    "smarts": item.smarts,
                    "pattern_source": item.pattern_source,
                    "occurrences": item.occurrences,
                }
                for item in result.functional_groups
            ],
            "structural_teaching": result.structural_teaching,
            "code": result.code,
            "message": result.message,
        },
        from_attributes=True,
    )


router = APIRouter(prefix="/v1/structures", tags=["structure-lab"])
engine = RdkitChemistryEngine()


@router.post("/analyze", response_model=AnalyzeStructureResponse)
def analyze(request: AnalyzeStructureRequest) -> AnalyzeStructureResponse:
    return _to_response(
        analyze_structure(input_format=request.format, text=request.text, engine=engine)
    )
