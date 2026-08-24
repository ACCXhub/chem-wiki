"""PostgreSQL repository adapter for the canonical M05 Reaction document."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from chem_wiki.modules.chemistry_core import (
    Condition,
    IonId,
    Phase,
    ProvenanceRef,
    Reaction,
    ReactionCode,
    ReactionId,
    ReactionParticipant,
    ReactionParticipantId,
    ReactionRole,
    ReactionStatus,
    StoichiometricCoefficient,
    SubstanceId,
)

from .application import PhenomenonFact, ReactionDocument, ReviewedRedoxMetadata
from .equation import EquationMode
from .persistence import (
    ReactionConditionRow,
    ReactionParticipantRow,
    ReactionPhenomenonRow,
    ReactionPhenomenonSourceRow,
    ReactionRow,
    ReactionSourceRow,
)


class PostgresReactionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: ReactionDocument) -> None:
        reaction = document.reaction
        redox = document.redox_metadata
        self._session.add(
            ReactionRow(
                id=reaction.id.value,
                reaction_code=reaction.code.value,
                equation_text=document.equation_text,
                equation_mode=document.equation_mode.value,
                reaction_type=document.reaction_type,
                reversible=reaction.reversible,
                exam_heat=document.exam_heat,
                status=reaction.status.value,
                conservation_state=document.conservation_state,
                redox_metadata=(
                    {
                        "oxidized_species": redox.oxidized_species,
                        "reduced_species": redox.reduced_species,
                        "electron_count": redox.electron_count,
                        "explanation": redox.explanation,
                    }
                    if redox
                    else None
                ),
                reviewed_by=document.reviewed_by,
                reviewed_at=document.reviewed_at,
            )
        )
        self._session.flush()
        for ordinal, participant in enumerate(reaction.participants):
            target_type = "substance" if isinstance(participant.target, SubstanceId) else "ion"
            self._session.add(
                ReactionParticipantRow(
                    id=participant.id.value,
                    reaction_id=reaction.id.value,
                    target_type=target_type,
                    target_id=participant.target.value,
                    role=participant.role.value,
                    stoichiometry=participant.stoichiometry.value,
                    phase=participant.phase.value if participant.phase else None,
                    ordinal=ordinal,
                )
            )
        for ordinal, condition in enumerate(reaction.conditions):
            self._session.add(
                ReactionConditionRow(
                    reaction_id=reaction.id.value,
                    ordinal=ordinal,
                    kind=condition.kind,
                    value_text=condition.value if isinstance(condition.value, str) else None,
                    value_decimal=(
                        condition.value if isinstance(condition.value, Decimal) else None
                    ),
                    unit=condition.unit,
                )
            )
        for ordinal, source in enumerate(reaction.provenance):
            self._session.add(
                ReactionSourceRow(
                    reaction_id=reaction.id.value,
                    ordinal=ordinal,
                    source_id=source.source_id,
                    source_url=source.source_url,
                    citation=source.citation,
                    retrieved_at=source.retrieved_at,
                    source_version=source.source_version,
                )
            )
        for ordinal, phenomenon in enumerate(document.phenomena):
            self._session.add(
                ReactionPhenomenonRow(
                    id=phenomenon.id,
                    reaction_id=reaction.id.value,
                    ordinal=ordinal,
                    name=phenomenon.name,
                    category=phenomenon.category,
                    description=phenomenon.description,
                )
            )
            for source_ordinal, source in enumerate(phenomenon.provenance):
                self._session.add(
                    ReactionPhenomenonSourceRow(
                        phenomenon_id=phenomenon.id,
                        ordinal=source_ordinal,
                        source_id=source.source_id,
                        source_url=source.source_url,
                        citation=source.citation,
                        retrieved_at=source.retrieved_at,
                        source_version=source.source_version,
                    )
                )

    def get(self, reaction_id: UUID) -> ReactionDocument | None:
        row = self._session.get(ReactionRow, reaction_id)
        if row is None:
            return None
        participant_rows = self._session.scalars(
            select(ReactionParticipantRow)
            .where(ReactionParticipantRow.reaction_id == reaction_id)
            .order_by(ReactionParticipantRow.ordinal)
        ).all()
        condition_rows = self._session.scalars(
            select(ReactionConditionRow)
            .where(ReactionConditionRow.reaction_id == reaction_id)
            .order_by(ReactionConditionRow.ordinal)
        ).all()
        source_rows = self._session.scalars(
            select(ReactionSourceRow)
            .where(ReactionSourceRow.reaction_id == reaction_id)
            .order_by(ReactionSourceRow.ordinal)
        ).all()
        phenomenon_rows = self._session.scalars(
            select(ReactionPhenomenonRow)
            .where(ReactionPhenomenonRow.reaction_id == reaction_id)
            .order_by(ReactionPhenomenonRow.ordinal)
        ).all()

        participants = tuple(
            ReactionParticipant(
                id=ReactionParticipantId(item.id),
                target=(
                    SubstanceId(item.target_id)
                    if item.target_type == "substance"
                    else IonId(item.target_id)
                ),
                role=ReactionRole(item.role),
                stoichiometry=StoichiometricCoefficient(item.stoichiometry),
                phase=Phase(item.phase) if item.phase else None,
            )
            for item in participant_rows
        )
        conditions = tuple(
            Condition(
                kind=item.kind,
                value=item.value_decimal if item.value_decimal is not None else item.value_text,
                unit=item.unit,
            )
            for item in condition_rows
        )
        provenance = tuple(
            ProvenanceRef(
                source_id=item.source_id,
                source_url=item.source_url,
                citation=item.citation,
                retrieved_at=item.retrieved_at,
                source_version=item.source_version,
            )
            for item in source_rows
        )
        phenomena: list[PhenomenonFact] = []
        for phenomenon in phenomenon_rows:
            phenomenon_sources = self._session.scalars(
                select(ReactionPhenomenonSourceRow)
                .where(ReactionPhenomenonSourceRow.phenomenon_id == phenomenon.id)
                .order_by(ReactionPhenomenonSourceRow.ordinal)
            ).all()
            phenomena.append(
                PhenomenonFact(
                    id=phenomenon.id,
                    name=phenomenon.name,
                    category=phenomenon.category,
                    description=phenomenon.description,
                    provenance=tuple(
                        ProvenanceRef(
                            source_id=item.source_id,
                            source_url=item.source_url,
                            citation=item.citation,
                            retrieved_at=item.retrieved_at,
                            source_version=item.source_version,
                        )
                        for item in phenomenon_sources
                    ),
                )
            )
        metadata = row.redox_metadata
        redox = (
            ReviewedRedoxMetadata(
                oxidized_species=str(metadata["oxidized_species"]),
                reduced_species=str(metadata["reduced_species"]),
                electron_count=int(metadata["electron_count"]),
                explanation=str(metadata["explanation"]),
            )
            if metadata
            else None
        )
        reaction = Reaction(
            id=ReactionId(row.id),
            code=ReactionCode(row.reaction_code),
            participants=participants,
            conditions=conditions,
            status=ReactionStatus(row.status),
            reversible=row.reversible,
            provenance=provenance,
        )
        return ReactionDocument(
            reaction=reaction,
            equation_text=row.equation_text,
            equation_mode=EquationMode(row.equation_mode),
            reaction_type=row.reaction_type,
            exam_heat=row.exam_heat,
            conservation_state=row.conservation_state,  # type: ignore[arg-type]
            phenomena=tuple(phenomena),
            redox_metadata=redox,
            reviewed_by=row.reviewed_by,
            reviewed_at=row.reviewed_at,
        )
