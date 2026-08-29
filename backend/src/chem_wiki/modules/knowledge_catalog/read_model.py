"""Public DTOs for catalog search and reaction traceability."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
    source_type: Literal["concept", "phenomenon"]
    display_name_zh: str
    teaching_priority: str
    content_zh: str
    related_reaction_ids: list[str]
    related_species_ids: list[str]


class CatalogStructureEntry(CatalogDto):
    application_species_id: UUID
    published_structure_id: str
    structure_scope: str
    canonical_smiles: str | None
    isomeric_smiles: str | None
    molecular_formula: str | None
    formal_charge: int | None
