"""Public DTOs for catalog search and reaction traceability."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CatalogDto(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class CatalogSpeciesResult(CatalogDto):
    consolidated_id: str
    application_id: UUID
    entity_kind: Literal["ion", "substance"]
    name_zh: str
    name_en: str | None
    formula: str
    charge: int
    composition: dict[str, int] | None
    aliases: list[str]
    chemical_classifications: list[str]
    primary_category: str
    tags: list[str]
    default_priority: str
    default_palette_rank: int
    equation_modes: dict[str, str]


class CatalogReactionParticipantResult(CatalogDto):
    role: str
    coefficient: int | float | str
    species_id: str | None
    application_target_id: UUID | None
    target_type: Literal["ion", "substance"] | None
    non_species_ref: str | None
    source_species_ref: str
    formula_literal: str | None
    phase: str | None
    name_zh: str | None
    formula: str | None
    charge: int | None


class CatalogReactionResult(CatalogDto):
    consolidated_id: str
    application_reaction_id: UUID | None
    source_package: str
    source_id: str
    name_zh: str
    materialization_state: Literal["materialized", "catalog_only"]
    not_materialized_reasons: list[str]
    participants: list[CatalogReactionParticipantResult]
    reaction_types: list[str]
    conditions: list[str]
    equation: str | None
    equation_status: str | None
    reversible: bool | None
    provenance_refs: list[str]


class CatalogKnowledgeResult(CatalogDto):
    consolidated_id: str
    application_id: UUID
    source_package: str
    source_id: str
    source_type: str
    display_name_zh: str
    teaching_priority: str
    content_zh: str | None
    related_reaction_ids: list[str]
    related_species_ids: list[str]
    payload: dict[str, object]
    links: list["CatalogKnowledgeLinkResult"] = Field(default_factory=list)
    provenance_refs: list[str]
    sources: list["CatalogSourceAttributionResult"] = Field(default_factory=list)


class CatalogKnowledgeLinkResult(CatalogDto):
    relation: str
    target_kind: Literal["knowledge", "species", "structure", "element"]
    target_id: str
    resolution_method: str
    evidence_refs: list[str]


class CatalogStructureEntry(CatalogDto):
    application_species_id: UUID
    published_structure_id: str
    structure_scope: str
    canonical_smiles: str | None
    isomeric_smiles: str | None
    molecular_formula: str | None
    formal_charge: int | None


class CatalogRelatedSpeciesResult(CatalogSpeciesResult):
    structure_available: bool


class CatalogSourceAttributionResult(CatalogDto):
    name: str
    url: str | None


class CatalogSpeciesPhaseFact(CatalogDto):
    standard_phase: Literal["s", "l", "g", "aq"]
    allowed_teaching_phases: list[Literal["s", "l", "g", "aq"]]
    thermochemistry_available_phases: list[Literal["s", "l", "g", "aq"]]
    phase_conditions: list[dict[str, object]]
    reference_temperature_k: Decimal
    standard_pressure_bar: Decimal
    source_refs: list[str]
    sources: list[CatalogSourceAttributionResult] = Field(default_factory=list)


class CatalogSpeciesThermochemistry(CatalogDto):
    phase: Literal["s", "l", "g", "aq"]
    temperature_k: Decimal
    standard_pressure_bar: Decimal
    delta_f_h_kj_mol: Decimal | None
    delta_f_g_kj_mol: Decimal | None
    s_j_mol_k: Decimal | None
    cp_j_mol_k: Decimal | None
    method: str
    source_refs: list[str]
    sources: list[CatalogSourceAttributionResult] = Field(default_factory=list)


class CatalogPhaseTransition(CatalogDto):
    transition: str
    from_phase: Literal["s", "l", "g", "aq"]
    to_phase: Literal["s", "l", "g", "aq"]
    enthalpy_kj_mol: Decimal
    transition_temperature_k: Decimal
    method: str
    source_refs: list[str]
    sources: list[CatalogSourceAttributionResult] = Field(default_factory=list)


class CatalogBondEnthalpyResult(CatalogDto):
    bond_enthalpy_id: str
    atom1: str
    atom2: str
    bond_order: Decimal
    environment_key: str
    enthalpy_kj_mol: Decimal
    temperature_k: Decimal
    phase_scope: str
    method: str
    qualifier: str
    source_refs: list[str]
    sources: list[CatalogSourceAttributionResult] = Field(default_factory=list)


class CatalogSpeciesThermochemistryContext(CatalogDto):
    consolidated_species_id: str
    application_species_id: UUID
    phase_fact: CatalogSpeciesPhaseFact
    thermochemistry: list[CatalogSpeciesThermochemistry]
    phase_transitions: list[CatalogPhaseTransition]


class CatalogReactionDetail(CatalogReactionResult):
    concepts: list[CatalogKnowledgeResult]
    phenomena: list[CatalogKnowledgeResult]
    related_species: list[CatalogRelatedSpeciesResult]
    sources: list[CatalogSourceAttributionResult]
