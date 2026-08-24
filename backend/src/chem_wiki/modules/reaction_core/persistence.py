"""PostgreSQL schema owned by M05 Reaction Core."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ReactionCoreBase(DeclarativeBase):
    pass


class ReactionRow(ReactionCoreBase):
    __tablename__ = "reaction"
    __table_args__ = (
        CheckConstraint(
            "equation_mode IN ('molecular', 'ionic', 'net_ionic')",
            name="ck_reaction_equation_mode",
        ),
        CheckConstraint(
            "status IN ('draft', 'review', 'published', 'archived')",
            name="ck_reaction_status",
        ),
        CheckConstraint(
            "conservation_state IN ('balanced', 'unbalanced', 'invalid')",
            name="ck_reaction_conservation_state",
        ),
        CheckConstraint("exam_heat BETWEEN 0 AND 1", name="ck_reaction_exam_heat"),
        CheckConstraint(
            "status <> 'published' OR conservation_state = 'balanced'",
            name="ck_reaction_published_balanced",
        ),
        CheckConstraint(
            "status <> 'published' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_reaction_published_reviewed",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    reaction_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    equation_text: Mapped[str] = mapped_column(Text, nullable=False)
    equation_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    reaction_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reversible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exam_heat: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    conservation_state: Mapped[str] = mapped_column(String(16), nullable=False)
    redox_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    reviewed_by: Mapped[str | None] = mapped_column(String(160))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReactionParticipantRow(ReactionCoreBase):
    __tablename__ = "reaction_participant"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('substance', 'ion')",
            name="ck_reaction_participant_target_type",
        ),
        CheckConstraint(
            "role IN ('reactant', 'product', 'catalyst', 'solvent')",
            name="ck_reaction_participant_role",
        ),
        CheckConstraint("stoichiometry > 0", name="ck_reaction_participant_stoichiometry"),
        UniqueConstraint(
            "reaction_id",
            "target_type",
            "target_id",
            "role",
            name="uq_reaction_participant_target_role",
        ),
        UniqueConstraint("reaction_id", "ordinal", name="uq_reaction_participant_ordinal"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    reaction_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("reaction.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    stoichiometry: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    phase: Mapped[str | None] = mapped_column(String(16))
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)


class ReactionConditionRow(ReactionCoreBase):
    __tablename__ = "reaction_condition"
    __table_args__ = (
        CheckConstraint(
            "NOT (value_text IS NOT NULL AND value_decimal IS NOT NULL)",
            name="ck_reaction_condition_value_shape",
        ),
    )

    reaction_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("reaction.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    value_text: Mapped[str | None] = mapped_column(String(160))
    value_decimal: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    unit: Mapped[str | None] = mapped_column(String(32))


class ReactionSourceRow(ReactionCoreBase):
    __tablename__ = "reaction_source"
    __table_args__ = (
        UniqueConstraint("reaction_id", "source_id", name="uq_reaction_source_identity"),
    )

    reaction_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("reaction.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    citation: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str | None] = mapped_column(String(120))


class ReactionPhenomenonRow(ReactionCoreBase):
    __tablename__ = "reaction_phenomenon"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    reaction_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("reaction.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class ReactionPhenomenonSourceRow(ReactionCoreBase):
    __tablename__ = "reaction_phenomenon_source"

    phenomenon_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("reaction_phenomenon.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    citation: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str | None] = mapped_column(String(120))
