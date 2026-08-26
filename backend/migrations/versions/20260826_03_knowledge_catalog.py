"""Knowledge catalog consumer persistence.

Revision ID: 20260826_03
Revises: 20260824_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260826_03"
down_revision: str | None = "20260824_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_release",
        sa.Column("release", sa.String(80), primary_key=True),
        sa.Column("repository", sa.Text(), nullable=False),
        sa.Column("commit", sa.String(40), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "catalog_release_artifact",
        sa.Column(
            "release",
            sa.String(80),
            sa.ForeignKey("catalog_release.release", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("artifact_name", sa.String(120), primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("records", sa.Integer(), nullable=False),
    )
    op.create_table(
        "catalog_species",
        sa.Column("consolidated_id", sa.String(200), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_kind", sa.String(16), nullable=False),
        sa.Column("source_ids", postgresql.JSONB(), nullable=False),
        sa.Column("name_zh", sa.String(160), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=True),
        sa.Column("formula", sa.String(160), nullable=False),
        sa.Column("charge", sa.Integer(), nullable=False),
        sa.Column("composition", postgresql.JSONB(), nullable=True),
        sa.Column("aliases", postgresql.JSONB(), nullable=False),
        sa.Column("chemical_classifications", postgresql.JSONB(), nullable=False),
        sa.Column("teaching_priority", sa.String(16), nullable=False),
        sa.Column("source_review_states", postgresql.JSONB(), nullable=False),
        sa.Column("integration_status", sa.String(24), nullable=False),
        sa.Column("provenance_refs", postgresql.JSONB(), nullable=False),
        sa.Column("external_ids", postgresql.JSONB(), nullable=False),
        sa.Column("preferred_structure_id", sa.String(120), nullable=True),
        sa.CheckConstraint("entity_kind IN ('ion', 'substance')", name="ck_catalog_species_kind"),
        sa.CheckConstraint(
            "charge <> 0 OR entity_kind = 'substance'", name="ck_catalog_ion_charge"
        ),
        sa.UniqueConstraint("application_id", name="uq_catalog_species_application_id"),
    )
    op.create_index("ix_catalog_species_entity_kind", "catalog_species", ["entity_kind"])
    op.create_index("ix_catalog_species_name_zh", "catalog_species", ["name_zh"])
    op.create_index("ix_catalog_species_formula", "catalog_species", ["formula"])
    op.create_table(
        "catalog_source_crosswalk",
        sa.Column("source_package", sa.String(24), primary_key=True),
        sa.Column("source_id", sa.String(200), primary_key=True),
        sa.Column("source_entity_type", sa.String(16), nullable=False),
        sa.Column(
            "consolidated_id",
            sa.String(200),
            sa.ForeignKey("catalog_species.consolidated_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("mapping_status", sa.String(24), nullable=False),
        sa.Column("resolution_method", sa.String(48), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_catalog_source_crosswalk_consolidated_id",
        "catalog_source_crosswalk",
        ["consolidated_id"],
    )
    op.create_table(
        "catalog_teaching_projection",
        sa.Column(
            "species_id",
            sa.String(200),
            sa.ForeignKey("catalog_species.consolidated_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("primary_category", sa.String(32), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("search_tokens", postgresql.JSONB(), nullable=False),
        sa.Column("default_priority", sa.String(16), nullable=False),
        sa.Column("default_palette_rank", sa.Integer(), nullable=False),
        sa.Column("molecular_suitability", sa.String(16), nullable=False),
        sa.Column("ionic_suitability", sa.String(16), nullable=False),
        sa.Column("net_ionic_suitability", sa.String(16), nullable=False),
        sa.CheckConstraint("default_palette_rank >= 0", name="ck_catalog_palette_rank"),
        sa.UniqueConstraint("default_palette_rank", name="uq_catalog_palette_rank"),
    )
    op.create_index(
        "ix_catalog_teaching_projection_primary_category",
        "catalog_teaching_projection",
        ["primary_category"],
    )
    op.create_table(
        "catalog_structure_link",
        sa.Column("source_link_id", sa.String(160), primary_key=True),
        sa.Column(
            "species_id",
            sa.String(200),
            sa.ForeignKey("catalog_species.consolidated_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("application_species_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_package", sa.String(24), nullable=False),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.Column("published_structure_id", sa.String(120), nullable=False),
        sa.Column("application_structure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation", sa.String(48), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_catalog_structure_link_species_id", "catalog_structure_link", ["species_id"]
    )
    op.create_index(
        "ix_catalog_structure_link_application_species_id",
        "catalog_structure_link",
        ["application_species_id"],
    )
    op.create_index(
        "ix_catalog_structure_link_published_structure_id",
        "catalog_structure_link",
        ["published_structure_id"],
    )
    op.create_index(
        "ix_catalog_structure_link_application_structure_id",
        "catalog_structure_link",
        ["application_structure_id"],
    )
    op.create_table(
        "catalog_reaction",
        sa.Column("consolidated_id", sa.String(200), primary_key=True),
        sa.Column("application_reaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_package", sa.String(24), nullable=False),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.Column("name_zh", sa.String(240), nullable=False),
        sa.Column("materialization_state", sa.String(24), nullable=False),
        sa.Column("not_materialized_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("original_payload", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "materialization_state IN ('materialized', 'catalog_only')",
            name="ck_catalog_reaction_materialization_state",
        ),
        sa.CheckConstraint(
            "(materialization_state = 'materialized' AND application_reaction_id IS NOT NULL) "
            "OR (materialization_state = 'catalog_only' AND application_reaction_id IS NULL)",
            name="ck_catalog_reaction_application_identity",
        ),
        sa.UniqueConstraint("application_reaction_id", name="uq_catalog_reaction_application_id"),
    )
    op.create_index(
        "ix_catalog_reaction_application_reaction_id",
        "catalog_reaction",
        ["application_reaction_id"],
    )
    op.create_index("ix_catalog_reaction_name_zh", "catalog_reaction", ["name_zh"])
    op.create_index(
        "ix_catalog_reaction_materialization_state",
        "catalog_reaction",
        ["materialization_state"],
    )
    op.create_table(
        "catalog_reaction_participant",
        sa.Column(
            "reaction_id",
            sa.String(200),
            sa.ForeignKey("catalog_reaction.consolidated_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("coefficient_text", sa.String(64), nullable=False),
        sa.Column(
            "species_id",
            sa.String(200),
            sa.ForeignKey("catalog_species.consolidated_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("application_target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_type", sa.String(16), nullable=True),
        sa.Column("non_species_ref", sa.String(240), nullable=True),
        sa.Column("source_species_ref", sa.String(240), nullable=False),
        sa.Column("formula_literal", sa.String(160), nullable=True),
        sa.Column("phase", sa.String(24), nullable=True),
    )
    op.create_index(
        "ix_catalog_reaction_participant_species_id",
        "catalog_reaction_participant",
        ["species_id"],
    )
    op.create_index(
        "ix_catalog_reaction_participant_application_target_id",
        "catalog_reaction_participant",
        ["application_target_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_reaction_participant_application_target_id",
        table_name="catalog_reaction_participant",
    )
    op.drop_index(
        "ix_catalog_reaction_participant_species_id",
        table_name="catalog_reaction_participant",
    )
    op.drop_table("catalog_reaction_participant")
    op.drop_index("ix_catalog_reaction_materialization_state", table_name="catalog_reaction")
    op.drop_index("ix_catalog_reaction_name_zh", table_name="catalog_reaction")
    op.drop_index("ix_catalog_reaction_application_reaction_id", table_name="catalog_reaction")
    op.drop_table("catalog_reaction")
    op.drop_index(
        "ix_catalog_structure_link_application_structure_id",
        table_name="catalog_structure_link",
    )
    op.drop_index(
        "ix_catalog_structure_link_published_structure_id",
        table_name="catalog_structure_link",
    )
    op.drop_index(
        "ix_catalog_structure_link_application_species_id",
        table_name="catalog_structure_link",
    )
    op.drop_index("ix_catalog_structure_link_species_id", table_name="catalog_structure_link")
    op.drop_table("catalog_structure_link")
    op.drop_index(
        "ix_catalog_teaching_projection_primary_category",
        table_name="catalog_teaching_projection",
    )
    op.drop_table("catalog_teaching_projection")
    op.drop_index(
        "ix_catalog_source_crosswalk_consolidated_id",
        table_name="catalog_source_crosswalk",
    )
    op.drop_table("catalog_source_crosswalk")
    op.drop_index("ix_catalog_species_formula", table_name="catalog_species")
    op.drop_index("ix_catalog_species_name_zh", table_name="catalog_species")
    op.drop_index("ix_catalog_species_entity_kind", table_name="catalog_species")
    op.drop_table("catalog_species")
    op.drop_table("catalog_release_artifact")
    op.drop_table("catalog_release")
