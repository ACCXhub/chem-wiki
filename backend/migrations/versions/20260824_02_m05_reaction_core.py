"""M05 Reaction Core persistence.

Revision ID: 20260824_02
Revises: 20260820_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260824_02"
down_revision: str | None = "20260820_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reaction",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reaction_code", sa.String(80), nullable=False),
        sa.Column("equation_text", sa.Text(), nullable=False),
        sa.Column("equation_mode", sa.String(16), nullable=False),
        sa.Column("reaction_type", sa.String(80), nullable=False),
        sa.Column("reversible", sa.Boolean(), nullable=False),
        sa.Column("exam_heat", sa.Numeric(6, 4), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("conservation_state", sa.String(16), nullable=False),
        sa.Column("redox_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("reviewed_by", sa.String(160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "equation_mode IN ('molecular', 'ionic', 'net_ionic')",
            name="ck_reaction_equation_mode",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'review', 'published', 'archived')",
            name="ck_reaction_status",
        ),
        sa.CheckConstraint(
            "conservation_state IN ('balanced', 'unbalanced', 'invalid')",
            name="ck_reaction_conservation_state",
        ),
        sa.CheckConstraint("exam_heat BETWEEN 0 AND 1", name="ck_reaction_exam_heat"),
        sa.CheckConstraint(
            "status <> 'published' OR conservation_state = 'balanced'",
            name="ck_reaction_published_balanced",
        ),
        sa.CheckConstraint(
            "status <> 'published' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_reaction_published_reviewed",
        ),
        sa.UniqueConstraint("reaction_code", name="uq_reaction_reaction_code"),
    )
    op.create_index("ix_reaction_reaction_type", "reaction", ["reaction_type"])
    op.create_index("ix_reaction_status", "reaction", ["status"])
    op.create_table(
        "reaction_participant",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reaction.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("stoichiometry", sa.Numeric(20, 8), nullable=False),
        sa.Column("phase", sa.String(16), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "target_type IN ('substance', 'ion')",
            name="ck_reaction_participant_target_type",
        ),
        sa.CheckConstraint(
            "role IN ('reactant', 'product', 'catalyst', 'solvent')",
            name="ck_reaction_participant_role",
        ),
        sa.CheckConstraint("stoichiometry > 0", name="ck_reaction_participant_stoichiometry"),
        sa.UniqueConstraint(
            "reaction_id",
            "target_type",
            "target_id",
            "role",
            name="uq_reaction_participant_target_role",
        ),
        sa.UniqueConstraint("reaction_id", "ordinal", name="uq_reaction_participant_ordinal"),
    )
    op.create_index("ix_reaction_participant_reaction_id", "reaction_participant", ["reaction_id"])
    op.create_table(
        "reaction_condition",
        sa.Column(
            "reaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reaction.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("value_text", sa.String(160), nullable=True),
        sa.Column("value_decimal", sa.Numeric(20, 8), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.CheckConstraint(
            "NOT (value_text IS NOT NULL AND value_decimal IS NOT NULL)",
            name="ck_reaction_condition_value_shape",
        ),
    )
    op.create_table(
        "reaction_source",
        sa.Column(
            "reaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reaction.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_version", sa.String(120), nullable=True),
        sa.UniqueConstraint("reaction_id", "source_id", name="uq_reaction_source_identity"),
    )
    op.create_table(
        "reaction_phenomenon",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reaction.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_index("ix_reaction_phenomenon_reaction_id", "reaction_phenomenon", ["reaction_id"])
    op.create_index("ix_reaction_phenomenon_category", "reaction_phenomenon", ["category"])
    op.create_table(
        "reaction_phenomenon_source",
        sa.Column(
            "phenomenon_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reaction_phenomenon.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_version", sa.String(120), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("reaction_phenomenon_source")
    op.drop_index("ix_reaction_phenomenon_category", table_name="reaction_phenomenon")
    op.drop_index("ix_reaction_phenomenon_reaction_id", table_name="reaction_phenomenon")
    op.drop_table("reaction_phenomenon")
    op.drop_table("reaction_source")
    op.drop_table("reaction_condition")
    op.drop_index("ix_reaction_participant_reaction_id", table_name="reaction_participant")
    op.drop_table("reaction_participant")
    op.drop_index("ix_reaction_status", table_name="reaction")
    op.drop_index("ix_reaction_reaction_type", table_name="reaction")
    op.drop_table("reaction")
