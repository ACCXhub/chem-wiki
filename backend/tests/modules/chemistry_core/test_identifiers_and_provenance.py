from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.identifiers import (
    ElementId,
    FunctionalGroupId,
    IonId,
    ReactionId,
    ReactionParticipantId,
    StructureId,
    SubstanceId,
)
from chem_wiki.modules.chemistry_core.provenance import ProvenanceRef


@pytest.mark.parametrize(
    "id_type",
    [
        ElementId,
        IonId,
        SubstanceId,
        StructureId,
        FunctionalGroupId,
        ReactionId,
        ReactionParticipantId,
    ],
)
def test_chemistry_core_ids_preserve_uuid_value(id_type: type) -> None:
    value = uuid4()

    assert id_type(value).value == value


def test_different_id_types_are_not_equal() -> None:
    value = uuid4()

    assert ElementId(value) != SubstanceId(value)


def test_chemistry_core_ids_are_immutable() -> None:
    identity = ElementId(uuid4())

    with pytest.raises(FrozenInstanceError):
        identity.value = uuid4()  # type: ignore[misc]


def test_provenance_requires_non_blank_source_id() -> None:
    with pytest.raises(ValueError, match="source_id"):
        ProvenanceRef(source_id=" ")


def test_provenance_keeps_optional_traceability_fields() -> None:
    retrieved_at = datetime(2026, 8, 20, tzinfo=UTC)

    provenance = ProvenanceRef(
        source_id=" nist-webbook ",
        source_url="https://example.test/source",
        citation="Example citation",
        retrieved_at=retrieved_at,
        source_version="2026-08",
    )

    assert provenance.source_id == "nist-webbook"
    assert provenance.source_url == "https://example.test/source"
    assert provenance.citation == "Example citation"
    assert provenance.retrieved_at == retrieved_at
    assert provenance.source_version == "2026-08"


def test_provenance_is_immutable() -> None:
    provenance = ProvenanceRef(source_id="nist-webbook")

    with pytest.raises(FrozenInstanceError):
        provenance.source_id = "other-source"  # type: ignore[misc]
