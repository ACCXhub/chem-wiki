"""Phase 1 catalog knowledge and structure projections.

Revision ID: 20260828_04
Revises: 20260826_03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260828_04"
down_revision: str | None = "20260826_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_structure_record",
        sa.Column("published_structure_id", sa.String(120), primary_key=True),
        sa.Column("structure_scope", sa.String(32), nullable=False),
        sa.Column("canonical_smiles", sa.Text(), nullable=True),
        sa.Column("isomeric_smiles", sa.Text(), nullable=True),
        sa.Column("molecular_formula", sa.String(160), nullable=True),
        sa.Column("formal_charge", sa.Integer(), nullable=True),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "catalog_knowledge_record",
        sa.Column("consolidated_id", sa.String(240), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_package", sa.String(24), nullable=False),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("display_name_zh", sa.String(240), nullable=False),
        sa.Column("teaching_priority", sa.String(16), nullable=False),
        sa.Column("content_zh", sa.Text(), nullable=False),
        sa.Column("related_reaction_ids", postgresql.JSONB(), nullable=False),
        sa.Column("related_species_ids", postgresql.JSONB(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("provenance_refs", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('concept', 'phenomenon')",
            name="ck_catalog_knowledge_record_type",
        ),
        sa.UniqueConstraint("application_id", name="uq_catalog_knowledge_record_application_id"),
    )
    op.create_index(
        "ix_catalog_knowledge_record_source_package",
        "catalog_knowledge_record",
        ["source_package"],
    )
    op.create_index(
        "ix_catalog_knowledge_record_source_id",
        "catalog_knowledge_record",
        ["source_id"],
    )
    op.create_index(
        "ix_catalog_knowledge_record_source_type",
        "catalog_knowledge_record",
        ["source_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_knowledge_record_source_type", table_name="catalog_knowledge_record")
    op.drop_index("ix_catalog_knowledge_record_source_id", table_name="catalog_knowledge_record")
    op.drop_index(
        "ix_catalog_knowledge_record_source_package", table_name="catalog_knowledge_record"
    )
    op.drop_table("catalog_knowledge_record")
    op.drop_table("catalog_structure_record")
