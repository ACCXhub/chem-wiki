from uuid import UUID

from chem_wiki.modules.knowledge_catalog import (
    CatalogReactionParticipantResult,
    CatalogReactionResult,
)
from chem_wiki.modules.reaction_builder import rank_reaction_candidates


def _participant(role: str, identity: int, formula: str) -> CatalogReactionParticipantResult:
    application_id = UUID(int=identity)
    return CatalogReactionParticipantResult(
        role=role,
        coefficient=1,
        species_id=f"species:{formula}",
        application_target_id=application_id,
        target_type="substance",
        non_species_ref=None,
        source_species_ref=f"species:{formula}",
        formula_literal=formula,
        phase=None,
        name_zh=formula,
        formula=formula,
        charge=0,
    )


def _reaction(
    identity: str,
    reactants: list[tuple[int, str]],
    products: list[tuple[int, str]],
    *,
    reversible: bool = False,
    materialization_state: str = "materialized",
) -> CatalogReactionResult:
    return CatalogReactionResult(
        consolidated_id=identity,
        application_reaction_id=UUID(int=len(identity))
        if materialization_state == "materialized"
        else None,
        source_package="test",
        source_id=identity,
        name_zh=identity,
        materialization_state=materialization_state,
        not_materialized_reasons=[],
        participants=[
            *[_participant("reactant", value, formula) for value, formula in reactants],
            *[_participant("product", value, formula) for value, formula in products],
        ],
        reaction_types=[],
        conditions=[],
        equation=None,
        equation_status="canonical",
        reversible=reversible,
        provenance_refs=[],
    )


def test_more_anchors_narrow_candidates_and_product_anchors_participate() -> None:
    water = _reaction("reaction:water", [(1, "H2"), (2, "O2")], [(3, "H2O")])
    peroxide = _reaction("reaction:peroxide", [(1, "H2"), (2, "O2")], [(4, "H2O2")])

    broad = rank_reaction_candidates(
        [peroxide, water],
        reactant_application_ids=[UUID(int=1)],
        product_application_ids=[],
    )
    narrowed = rank_reaction_candidates(
        [peroxide, water],
        reactant_application_ids=[UUID(int=1), UUID(int=2)],
        product_application_ids=[UUID(int=3)],
    )

    assert {candidate.reaction.consolidated_id for candidate in broad} == {
        "reaction:peroxide",
        "reaction:water",
    }
    assert [candidate.reaction.consolidated_id for candidate in narrowed] == [
        "reaction:water"
    ]
    assert narrowed[0].completion_ratio == 1
    assert narrowed[0].missing_participant_count == 0


def test_reversible_reaction_supports_reverse_orientation_but_directional_does_not() -> None:
    reversible = _reaction(
        "reaction:reversible", [(1, "A")], [(2, "B")], reversible=True
    )
    directional = _reaction("reaction:directional", [(1, "A")], [(2, "B")])

    matches = rank_reaction_candidates(
        [directional, reversible],
        reactant_application_ids=[UUID(int=2)],
        product_application_ids=[UUID(int=1)],
    )

    assert [candidate.reaction.consolidated_id for candidate in matches] == [
        "reaction:reversible"
    ]
    assert matches[0].orientation == "reverse"


def test_ranking_is_deterministic_and_prefers_materialized_reactions() -> None:
    catalog_only = _reaction(
        "reaction:a-catalog",
        [(1, "A")],
        [(2, "B")],
        materialization_state="catalog_only",
    )
    materialized_b = _reaction("reaction:b", [(1, "A")], [(3, "C")])
    materialized_a = _reaction("reaction:a", [(1, "A")], [(4, "D")])

    matches = rank_reaction_candidates(
        [materialized_b, catalog_only, materialized_a],
        reactant_application_ids=[UUID(int=1)],
        product_application_ids=[],
    )

    assert [candidate.reaction.consolidated_id for candidate in matches] == [
        "reaction:a",
        "reaction:b",
        "reaction:a-catalog",
    ]
