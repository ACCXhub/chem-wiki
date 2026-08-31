"""HTTP boundary for M07 known-reaction discovery."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from chem_wiki.modules.knowledge_catalog import (
    CatalogReactionParticipantResult,
    CatalogReader,
    get_catalog_reader,
)

from .application import rank_reaction_candidates


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ReactionBuilderDto(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class ReactionCandidateRequest(ReactionBuilderDto):
    reactant_application_ids: list[UUID] = Field(default_factory=list, max_length=20)
    product_application_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @field_validator("reactant_application_ids", "product_application_ids")
    @classmethod
    def require_unique_side_anchors(cls, values: list[UUID]) -> list[UUID]:
        if len(values) != len(set(values)):
            raise ValueError("同一侧的物质 identity 不可重复")
        return values


class ReactionCandidateParticipant(ReactionBuilderDto):
    role: str
    coefficient: int | float | str
    species_id: str | None
    application_target_id: UUID | None
    target_type: Literal["ion", "substance"] | None
    non_species_ref: str | None
    name_zh: str | None
    formula: str | None
    charge: int | None
    phase: str | None


class ReactionCandidate(ReactionBuilderDto):
    consolidated_id: str
    application_reaction_id: UUID | None
    name_zh: str
    materialization_state: Literal["materialized", "catalog_only"]
    participants: list[ReactionCandidateParticipant]
    equation: str | None
    reversible: bool | None
    reaction_types: list[str]
    conditions: list[str]
    provenance_refs: list[str]
    source_package: str
    source_id: str
    orientation: Literal["canonical", "reverse"]
    matched_anchor_count: int
    completion_ratio: float
    missing_participant_count: int


class ReactionCandidateResponse(ReactionBuilderDto):
    candidates: list[ReactionCandidate]


router = APIRouter(prefix="/v1/reaction-builder", tags=["reaction-builder"])


def _participant_dto(
    participant: CatalogReactionParticipantResult,
) -> ReactionCandidateParticipant:
    return ReactionCandidateParticipant(
        role=participant.role,
        coefficient=participant.coefficient,
        species_id=participant.species_id,
        application_target_id=participant.application_target_id,
        target_type=participant.target_type,
        non_species_ref=participant.non_species_ref,
        name_zh=participant.name_zh,
        formula=participant.formula,
        charge=participant.charge,
        phase=participant.phase,
    )


@router.post("/candidates", response_model=ReactionCandidateResponse)
def find_candidates(
    request: ReactionCandidateRequest,
    reader: Annotated[CatalogReader, Depends(get_catalog_reader)],
) -> ReactionCandidateResponse:
    identities = [
        *request.reactant_application_ids,
        *request.product_application_ids,
    ]
    ranked = rank_reaction_candidates(
        reader.find_reactions_by_application_ids(identities),
        reactant_application_ids=request.reactant_application_ids,
        product_application_ids=request.product_application_ids,
    )
    return ReactionCandidateResponse(
        candidates=[
            ReactionCandidate(
                consolidated_id=candidate.reaction.consolidated_id,
                application_reaction_id=candidate.reaction.application_reaction_id,
                name_zh=candidate.reaction.name_zh,
                materialization_state=candidate.reaction.materialization_state,
                participants=[
                    _participant_dto(participant) for participant in candidate.reaction.participants
                ],
                equation=candidate.reaction.equation,
                reversible=candidate.reaction.reversible,
                reaction_types=candidate.reaction.reaction_types,
                conditions=candidate.reaction.conditions,
                provenance_refs=candidate.reaction.provenance_refs,
                source_package=candidate.reaction.source_package,
                source_id=candidate.reaction.source_id,
                orientation=candidate.orientation,
                matched_anchor_count=candidate.matched_anchor_count,
                completion_ratio=candidate.completion_ratio,
                missing_participant_count=candidate.missing_participant_count,
            )
            for candidate in ranked
        ]
    )
