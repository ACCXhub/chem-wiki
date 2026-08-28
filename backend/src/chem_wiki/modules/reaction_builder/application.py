"""M07 candidate matching and ranking over canonical catalog reactions."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from chem_wiki.modules.knowledge_catalog import CatalogReactionResult

ReactionOrientation = Literal["canonical", "reverse"]


@dataclass(frozen=True, slots=True)
class RankedReactionCandidate:
    reaction: CatalogReactionResult
    orientation: ReactionOrientation
    matched_anchor_count: int
    completion_ratio: float
    missing_participant_count: int


def _participant_ids(
    reaction: CatalogReactionResult, role: str
) -> set[UUID]:
    return {
        participant.application_target_id
        for participant in reaction.participants
        if participant.role == role and participant.application_target_id is not None
    }


def _compatible(
    reactant_anchors: set[UUID],
    product_anchors: set[UUID],
    reaction_reactants: set[UUID],
    reaction_products: set[UUID],
) -> bool:
    return reactant_anchors <= reaction_reactants and product_anchors <= reaction_products


def rank_reaction_candidates(
    reactions: list[CatalogReactionResult],
    *,
    reactant_application_ids: list[UUID],
    product_application_ids: list[UUID],
) -> list[RankedReactionCandidate]:
    """Return side-compatible candidates in a stable, domain-owned order."""

    reactant_anchors = set(reactant_application_ids)
    product_anchors = set(product_application_ids)
    if not reactant_anchors and not product_anchors:
        return []

    matched_anchor_count = len(reactant_anchors) + len(product_anchors)
    candidates: list[RankedReactionCandidate] = []
    for reaction in reactions:
        canonical_reactants = _participant_ids(reaction, "reactant")
        canonical_products = _participant_ids(reaction, "product")
        orientation: ReactionOrientation | None = None
        if _compatible(
            reactant_anchors,
            product_anchors,
            canonical_reactants,
            canonical_products,
        ):
            orientation = "canonical"
        elif reaction.reversible is True and _compatible(
            reactant_anchors,
            product_anchors,
            canonical_products,
            canonical_reactants,
        ):
            orientation = "reverse"
        if orientation is None:
            continue

        participant_count = len(reaction.participants)
        missing_count = max(0, participant_count - matched_anchor_count)
        completion_ratio = (
            matched_anchor_count / participant_count if participant_count else 0.0
        )
        candidates.append(
            RankedReactionCandidate(
                reaction=reaction,
                orientation=orientation,
                matched_anchor_count=matched_anchor_count,
                completion_ratio=completion_ratio,
                missing_participant_count=missing_count,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            -candidate.matched_anchor_count,
            -candidate.completion_ratio,
            candidate.missing_participant_count,
            0
            if candidate.reaction.materialization_state == "materialized"
            else 1,
            candidate.reaction.consolidated_id,
        )
    )
    return candidates
