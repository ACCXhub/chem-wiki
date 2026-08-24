from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.modules.chemistry_core import ProvenanceRef, ReactionRole, ReactionStatus
from chem_wiki.modules.reaction_core import (
    CreateReactionCommand,
    EquationMode,
    ParticipantCommand,
    PostgresReactionRepository,
    ReactionCoreBase,
    prepare_reaction,
)

BACKEND_ROOT = Path(__file__).parents[3]


@pytest.mark.integration
def test_postgres_repository_round_trips_stable_reaction_and_participant_identity() -> None:
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    reaction_id = UUID("a1111111-1111-4111-8111-111111111111")
    participant_ids = (
        UUID("a2222222-2222-4222-8222-222222222222"),
        UUID("a3333333-3333-4333-8333-333333333333"),
        UUID("a4444444-4444-4444-8444-444444444444"),
    )
    target_ids = (
        UUID("a5555555-5555-4555-8555-555555555555"),
        UUID("a6666666-6666-4666-8666-666666666666"),
        UUID("a7777777-7777-4777-8777-777777777777"),
    )
    document = prepare_reaction(
        CreateReactionCommand(
            id=reaction_id,
            reaction_code="m05-postgres-water",
            equation_text="2H2(g) + O2(g) -> 2H2O(l)",
            equation_mode=EquationMode.MOLECULAR,
            reaction_type="化合反应",
            exam_heat=Decimal("0.65"),
            participants=tuple(
                ParticipantCommand(
                    id=participant_id,
                    target_type="substance",
                    target_id=target_id,
                    role=(ReactionRole.REACTANT if index < 2 else ReactionRole.PRODUCT),
                    stoichiometry=Decimal((2, 1, 2)[index]),
                    phase=("g", "g", "l")[index],
                )
                for index, (participant_id, target_id) in enumerate(
                    zip(participant_ids, target_ids, strict=True)
                )
            ),
            status=ReactionStatus.PUBLISHED,
            provenance=(
                ProvenanceRef(
                    source_id="reviewed-test-source",
                    source_url="https://example.test/reaction/water",
                    citation="M05 deterministic fixture",
                    retrieved_at=datetime(2026, 8, 24, tzinfo=UTC),
                    source_version="v1",
                ),
            ),
            reviewed_by="reviewer@example.test",
            reviewed_at=datetime(2026, 8, 24, tzinfo=UTC),
        )
    )
    engine = create_engine(Settings().database_url)
    assert "reaction" in ReactionCoreBase.metadata.tables

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection) as session:
                repository = PostgresReactionRepository(session)
                repository.add(document)
                session.flush()
                session.expire_all()

                restored = repository.get(reaction_id)

                assert restored is not None
                assert restored.reaction.id.value == reaction_id
                assert [item.id.value for item in restored.reaction.participants] == list(
                    participant_ids
                )
                assert [item.target.value for item in restored.reaction.participants] == list(
                    target_ids
                )
                assert restored.equation_text == "2H₂(g) + O₂(g) → 2H₂O(l)"
                assert restored.reaction.provenance[0].source_id == "reviewed-test-source"
        finally:
            transaction.rollback()
            engine.dispose()
