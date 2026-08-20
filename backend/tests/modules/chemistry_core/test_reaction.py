from collections.abc import Callable
from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.identifiers import (
    IonId,
    ReactionId,
    ReactionParticipantId,
    SubstanceId,
)
from chem_wiki.modules.chemistry_core.provenance import ProvenanceRef
from chem_wiki.modules.chemistry_core.reaction import (
    Condition,
    Phase,
    Reaction,
    ReactionCode,
    ReactionParticipant,
    ReactionRole,
    ReactionStatus,
    StoichiometricCoefficient,
)


def _participant(
    role: ReactionRole,
    target: SubstanceId | IonId,
    *,
    participant_id: ReactionParticipantId | None = None,
) -> ReactionParticipant:
    return ReactionParticipant(
        id=participant_id or ReactionParticipantId(uuid4()),
        target=target,
        role=role,
        stoichiometry=StoichiometricCoefficient(Decimal(1)),
    )


@pytest.mark.parametrize("value", [Decimal(0), Decimal(-1)])
def test_stoichiometry_must_be_positive(value: Decimal) -> None:
    with pytest.raises(ValueError, match="stoichiometry"):
        StoichiometricCoefficient(value)


def test_condition_is_an_embedded_value_without_id() -> None:
    condition = Condition(kind=" temperature ", value=Decimal("298.15"), unit="K")

    assert condition.kind == "temperature"
    assert not hasattr(condition, "id")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ReactionCode(" "),
        lambda: Phase(" "),
        lambda: Condition(kind=" "),
        lambda: Condition(kind="temperature", value=" "),
        lambda: Condition(kind="temperature", value="298", unit=" "),
    ],
)
def test_reaction_text_values_reject_blank_content(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match="blank"):
        factory()


def test_reaction_code_is_normalized() -> None:
    assert ReactionCode(" rxn-1 ").value == "rxn-1"


def test_phase_is_normalized_without_freezing_a_taxonomy() -> None:
    assert Phase(" aqueous ").value == "aqueous"


def test_participant_target_accepts_only_substance_or_ion_id() -> None:
    with pytest.raises(TypeError, match="target"):
        ReactionParticipant(
            id=ReactionParticipantId(uuid4()),
            target="not-an-id",  # type: ignore[arg-type]
            role=ReactionRole.REACTANT,
            stoichiometry=StoichiometricCoefficient(Decimal(1)),
        )


def test_reaction_is_first_class_and_accepts_substance_to_ion_participants() -> None:
    reactant = _participant(ReactionRole.REACTANT, SubstanceId(uuid4()))
    product = _participant(ReactionRole.PRODUCT, IonId(uuid4()))
    condition = Condition(kind="temperature", value=Decimal(298), unit="K")
    provenance = ProvenanceRef(source_id="curriculum-review")

    reaction = Reaction(
        id=ReactionId(uuid4()),
        code=ReactionCode("rxn-1"),
        participants=(reactant, product),
        conditions=(condition,),
        provenance=(provenance,),
    )

    assert reaction.participants == (reactant, product)
    assert reaction.conditions == (condition,)
    assert reaction.status is ReactionStatus.DRAFT
    assert reaction.reversible is False
    assert reaction.provenance == (provenance,)


def test_participant_keeps_stable_id_and_relationship_provenance() -> None:
    participant_id = ReactionParticipantId(uuid4())
    provenance = ProvenanceRef(source_id="curriculum-review")

    participant = ReactionParticipant(
        id=participant_id,
        target=SubstanceId(uuid4()),
        role=ReactionRole.REACTANT,
        stoichiometry=StoichiometricCoefficient(Decimal(2)),
        phase=Phase("aqueous"),
        provenance=(provenance,),
    )

    assert participant.id == participant_id
    assert participant.provenance == (provenance,)


@pytest.mark.parametrize(
    ("roles", "message"),
    [((ReactionRole.PRODUCT,), "reactant"), ((ReactionRole.REACTANT,), "product")],
)
def test_reaction_requires_reactant_and_product(
    roles: tuple[ReactionRole, ...], message: str
) -> None:
    participants = tuple(_participant(role, SubstanceId(uuid4())) for role in roles)

    with pytest.raises(ValueError, match=message):
        Reaction(ReactionId(uuid4()), ReactionCode("rxn-1"), participants)


def test_reaction_rejects_duplicate_participant_ids() -> None:
    shared_id = ReactionParticipantId(uuid4())
    reactant = _participant(
        ReactionRole.REACTANT,
        SubstanceId(uuid4()),
        participant_id=shared_id,
    )
    product = _participant(
        ReactionRole.PRODUCT,
        IonId(uuid4()),
        participant_id=shared_id,
    )

    with pytest.raises(ValueError, match="participant id"):
        Reaction(ReactionId(uuid4()), ReactionCode("rxn-1"), (reactant, product))


def test_reaction_is_immutable() -> None:
    reaction = Reaction(
        id=ReactionId(uuid4()),
        code=ReactionCode("rxn-1"),
        participants=(
            _participant(ReactionRole.REACTANT, SubstanceId(uuid4())),
            _participant(ReactionRole.PRODUCT, IonId(uuid4())),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        reaction.reversible = True  # type: ignore[misc]
