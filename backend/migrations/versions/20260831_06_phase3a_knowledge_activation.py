"""Phase 3A generic knowledge and thermochemistry activation.

Revision ID: 20260831_06
Revises: 20260829_05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260831_06"
down_revision: str | None = "20260829_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_catalog_knowledge_record_type", "catalog_knowledge_record", type_="check"
    )
    op.alter_column(
        "catalog_knowledge_record",
        "source_type",
        existing_type=sa.String(24),
        type_=sa.String(64),
        existing_nullable=False,
    )
    op.alter_column(
        "catalog_knowledge_record",
        "content_zh",
        existing_type=sa.Text(),
        nullable=True,
    )

    op.create_table(
        "catalog_knowledge_link",
        sa.Column("link_id", sa.String(80), primary_key=True),
        sa.Column(
            "source_knowledge_id",
            sa.String(240),
            sa.ForeignKey("catalog_knowledge_record.consolidated_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation", sa.String(80), nullable=False),
        sa.Column("target_kind", sa.String(16), nullable=False),
        sa.Column("target_id", sa.String(240), nullable=False),
        sa.Column("resolution_method", sa.String(64), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "target_kind IN ('knowledge', 'species', 'structure', 'element')",
            name="ck_catalog_knowledge_link_target_kind",
        ),
    )
    op.create_index(
        "ix_catalog_knowledge_link_source_knowledge_id",
        "catalog_knowledge_link",
        ["source_knowledge_id"],
    )
    op.create_index(
        "ix_catalog_knowledge_link_target_kind",
        "catalog_knowledge_link",
        ["target_kind"],
    )
    op.create_index("ix_catalog_knowledge_link_target_id", "catalog_knowledge_link", ["target_id"])

    op.create_table(
        "catalog_species_phase_fact",
        sa.Column(
            "species_id",
            sa.String(200),
            sa.ForeignKey("catalog_species.consolidated_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("phase_fact_id", sa.String(240), nullable=False, unique=True),
        sa.Column("standard_phase", sa.String(2), nullable=False),
        sa.Column("allowed_teaching_phases", postgresql.JSONB(), nullable=False),
        sa.Column("thermochemistry_available_phases", postgresql.JSONB(), nullable=False),
        sa.Column("phase_conditions", postgresql.JSONB(), nullable=False),
        sa.Column("reference_temperature_k", sa.Numeric(10, 3), nullable=False),
        sa.Column("standard_pressure_bar", sa.Numeric(10, 3), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
    )
    op.create_table(
        "catalog_species_thermochemistry",
        sa.Column("thermochemistry_id", sa.String(240), primary_key=True),
        sa.Column(
            "species_id",
            sa.String(200),
            sa.ForeignKey("catalog_species.consolidated_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(2), nullable=False),
        sa.Column("temperature_k", sa.Numeric(10, 3), nullable=False),
        sa.Column("standard_pressure_bar", sa.Numeric(10, 3), nullable=False),
        sa.Column("delta_f_h_kj_mol", sa.Numeric(16, 6), nullable=True),
        sa.Column("delta_f_g_kj_mol", sa.Numeric(16, 6), nullable=True),
        sa.Column("s_j_mol_k", sa.Numeric(16, 6), nullable=True),
        sa.Column("cp_j_mol_k", sa.Numeric(16, 6), nullable=True),
        sa.Column("method", sa.String(120), nullable=False),
        sa.Column("source_species_name", sa.String(120), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.UniqueConstraint(
            "species_id",
            "phase",
            "temperature_k",
            "standard_pressure_bar",
            name="uq_catalog_species_thermochemistry_key",
        ),
    )
    op.create_index(
        "ix_catalog_species_thermochemistry_species_id",
        "catalog_species_thermochemistry",
        ["species_id"],
    )
    op.create_table(
        "catalog_phase_transition",
        sa.Column("transition_id", sa.String(240), primary_key=True),
        sa.Column(
            "species_id",
            sa.String(200),
            sa.ForeignKey("catalog_species.consolidated_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("transition", sa.String(48), nullable=False),
        sa.Column("from_phase", sa.String(2), nullable=False),
        sa.Column("to_phase", sa.String(2), nullable=False),
        sa.Column("enthalpy_kj_mol", sa.Numeric(16, 6), nullable=False),
        sa.Column("transition_temperature_k", sa.Numeric(10, 3), nullable=False),
        sa.Column("method", sa.String(160), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
    )
    op.create_index(
        "ix_catalog_phase_transition_species_id",
        "catalog_phase_transition",
        ["species_id"],
    )
    op.create_table(
        "catalog_bond_enthalpy",
        sa.Column("bond_enthalpy_id", sa.String(160), primary_key=True),
        sa.Column("atom1", sa.String(3), nullable=False),
        sa.Column("atom2", sa.String(3), nullable=False),
        sa.Column("bond_order", sa.Numeric(4, 2), nullable=False),
        sa.Column("environment_key", sa.String(200), nullable=False),
        sa.Column("enthalpy_kj_mol", sa.Numeric(16, 6), nullable=False),
        sa.Column("temperature_k", sa.Numeric(10, 3), nullable=False),
        sa.Column("phase_scope", sa.String(24), nullable=False),
        sa.Column("method", sa.String(160), nullable=False),
        sa.Column("qualifier", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("catalog_bond_enthalpy")
    op.drop_index("ix_catalog_phase_transition_species_id", table_name="catalog_phase_transition")
    op.drop_table("catalog_phase_transition")
    op.drop_index(
        "ix_catalog_species_thermochemistry_species_id",
        table_name="catalog_species_thermochemistry",
    )
    op.drop_table("catalog_species_thermochemistry")
    op.drop_table("catalog_species_phase_fact")
    op.drop_index("ix_catalog_knowledge_link_target_id", table_name="catalog_knowledge_link")
    op.drop_index("ix_catalog_knowledge_link_target_kind", table_name="catalog_knowledge_link")
    op.drop_index(
        "ix_catalog_knowledge_link_source_knowledge_id", table_name="catalog_knowledge_link"
    )
    op.drop_table("catalog_knowledge_link")
    op.execute(
        "DELETE FROM catalog_knowledge_record "
        "WHERE source_type NOT IN ('concept', 'phenomenon') OR content_zh IS NULL"
    )
    op.alter_column(
        "catalog_knowledge_record",
        "content_zh",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "catalog_knowledge_record",
        "source_type",
        existing_type=sa.String(64),
        type_=sa.String(24),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_catalog_knowledge_record_type",
        "catalog_knowledge_record",
        "source_type IN ('concept', 'phenomenon')",
    )
