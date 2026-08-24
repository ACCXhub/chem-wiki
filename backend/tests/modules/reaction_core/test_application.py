from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from chem_wiki.modules.chemistry_core import ProvenanceRef, ReactionRole, ReactionStatus
from chem_wiki.modules.reaction_core import (
    CreateReactionCommand,
    EquationMode,
    ParticipantCommand,
    prepare_reaction,
)

REACTION_ID = UUID("11111111-1111-4111-8111-111111111111")
H2_ID = UUID("22222222-2222-4222-8222-222222222222")
O2_ID = UUID("33333333-3333-4333-8333-333333333333")
H2O_ID = UUID("44444444-4444-4444-8444-444444444444")
H2_PARTICIPANT_ID = UUID("55555555-5555-4555-8555-555555555555")
O2_PARTICIPANT_ID = UUID("66666666-6666-4666-8666-666666666666")
H2O_PARTICIPANT_ID = UUID("77777777-7777-4777-8777-777777777777")


def _published_command() -> CreateReactionCommand:
    return CreateReactionCommand(
        id=REACTION_ID,
        reaction_code="water-formation",
        equation_text="2H2(g) + O2(g) -> 2H2O(l)",
        equation_mode=EquationMode.MOLECULAR,
        reaction_type="化合反应",
        reversible=False,
        exam_heat=Decimal("0.65"),
        participants=(
            ParticipantCommand(
                id=H2_PARTICIPANT_ID,
                target_type="substance",
                target_id=H2_ID,
                role=ReactionRole.REACTANT,
                stoichiometry=Decimal(2),
                phase="g",
            ),
            ParticipantCommand(
                id=O2_PARTICIPANT_ID,
                target_type="substance",
                target_id=O2_ID,
                role=ReactionRole.REACTANT,
                stoichiometry=Decimal(1),
                phase="g",
            ),
            ParticipantCommand(
                id=H2O_PARTICIPANT_ID,
                target_type="substance",
                target_id=H2O_ID,
                role=ReactionRole.PRODUCT,
                stoichiometry=Decimal(2),
                phase="l",
            ),
        ),
        status=ReactionStatus.PUBLISHED,
        provenance=(
            ProvenanceRef(
                source_id="reviewed-curriculum-source",
                citation="经审核的课程反应事实",
            ),
        ),
        reviewed_by="reviewer@example.test",
        reviewed_at=datetime(2026, 8, 24, tzinfo=UTC),
    )


def test_prepares_first_class_reaction_with_stable_participant_ids() -> None:
    document = prepare_reaction(_published_command())

    assert document.reaction.id.value == REACTION_ID
    assert [item.id.value for item in document.reaction.participants] == [
        H2_PARTICIPANT_ID,
        O2_PARTICIPANT_ID,
        H2O_PARTICIPANT_ID,
    ]
    assert [item.target.value for item in document.reaction.participants] == [
        H2_ID,
        O2_ID,
        H2O_ID,
    ]
    assert document.conservation_state == "balanced"
    assert document.equation_text == "2H₂(g) + O₂(g) → 2H₂O(l)"


def test_published_reaction_requires_reviewed_provenance() -> None:
    command = _published_command()

    with pytest.raises(ValueError, match="来源"):
        prepare_reaction(replace(command, provenance=()))


def test_published_reaction_requires_reviewer_identity_and_time() -> None:
    command = _published_command()

    with pytest.raises(ValueError, match="审核"):
        prepare_reaction(replace(command, reviewed_by=None))


def test_draft_preserves_explicit_unbalanced_state() -> None:
    command = _published_command()
    document = prepare_reaction(
        replace(
            command,
            equation_text="H2 + O2 -> H2O",
            status=ReactionStatus.DRAFT,
            provenance=(),
            reviewed_by=None,
            reviewed_at=None,
        )
    )

    assert document.conservation_state == "unbalanced"
    assert document.equation_text == "H2 + O2 -> H2O"


def test_published_reaction_rejects_participant_coefficients_that_do_not_match_equation() -> None:
    command = _published_command()
    participants = list(command.participants)
    participants[0] = replace(participants[0], stoichiometry=Decimal(1))

    with pytest.raises(ValueError, match="参与物系数"):
        prepare_reaction(replace(command, participants=tuple(participants)))
