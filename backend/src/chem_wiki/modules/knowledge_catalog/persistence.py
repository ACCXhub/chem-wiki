"""Application-owned persistence for the consolidated knowledge catalog."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class KnowledgeCatalogBase(DeclarativeBase):
    pass


class CatalogReleaseRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_release"

    release: Mapped[str] = mapped_column(String(80), primary_key=True)
    repository: Mapped[str] = mapped_column(Text, nullable=False)
    commit: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CatalogReleaseArtifactRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_release_artifact"

    release: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("catalog_release.release", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    records: Mapped[int] = mapped_column(Integer, nullable=False)


class CatalogSpeciesRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_species"
    __table_args__ = (
        CheckConstraint("entity_kind IN ('ion', 'substance')", name="ck_catalog_species_kind"),
        CheckConstraint("charge <> 0 OR entity_kind = 'substance'", name="ck_catalog_ion_charge"),
        UniqueConstraint("application_id", name="uq_catalog_species_application_id"),
    )

    consolidated_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    application_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    entity_kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    source_ids: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    name_zh: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    name_en: Mapped[str | None] = mapped_column(String(200))
    formula: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    charge: Mapped[int] = mapped_column(Integer, nullable=False)
    composition: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    chemical_classifications: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    teaching_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    source_review_states: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    integration_status: Mapped[str] = mapped_column(String(24), nullable=False)
    provenance_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    external_ids: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    preferred_structure_id: Mapped[str | None] = mapped_column(String(120))


class CatalogSourceCrosswalkRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_source_crosswalk"

    source_package: Mapped[str] = mapped_column(String(24), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    source_entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    consolidated_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("catalog_species.consolidated_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    mapping_status: Mapped[str] = mapped_column(String(24), nullable=False)
    resolution_method: Mapped[str] = mapped_column(String(48), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class CatalogTeachingProjectionRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_teaching_projection"
    __table_args__ = (
        CheckConstraint("default_palette_rank >= 0", name="ck_catalog_palette_rank"),
        UniqueConstraint("default_palette_rank", name="uq_catalog_palette_rank"),
    )

    species_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("catalog_species.consolidated_id", ondelete="CASCADE"),
        primary_key=True,
    )
    primary_category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    search_tokens: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    default_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    default_palette_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    molecular_suitability: Mapped[str] = mapped_column(String(16), nullable=False)
    ionic_suitability: Mapped[str] = mapped_column(String(16), nullable=False)
    net_ionic_suitability: Mapped[str] = mapped_column(String(16), nullable=False)


class CatalogStructureLinkRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_structure_link"

    source_link_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    species_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("catalog_species.consolidated_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_species_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False, index=True
    )
    source_package: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)
    published_structure_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    application_structure_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False, index=True
    )
    relation: Mapped[str] = mapped_column(String(48), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class CatalogStructureRecordRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_structure_record"

    published_structure_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    structure_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_smiles: Mapped[str | None] = mapped_column(Text)
    isomeric_smiles: Mapped[str | None] = mapped_column(Text)
    molecular_formula: Mapped[str | None] = mapped_column(String(160))
    formal_charge: Mapped[int | None] = mapped_column(Integer)
    provenance: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)


class CatalogKnowledgeRecordRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_knowledge_record"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('concept', 'phenomenon')",
            name="ck_catalog_knowledge_record_type",
        ),
        UniqueConstraint("application_id", name="uq_catalog_knowledge_record_application_id"),
    )

    consolidated_id: Mapped[str] = mapped_column(String(240), primary_key=True)
    application_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    source_package: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    display_name_zh: Mapped[str] = mapped_column(String(240), nullable=False)
    teaching_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    content_zh: Mapped[str] = mapped_column(Text, nullable=False)
    related_reaction_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    related_species_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    provenance_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class CatalogReactionRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_reaction"
    __table_args__ = (
        CheckConstraint(
            "materialization_state IN ('materialized', 'catalog_only')",
            name="ck_catalog_reaction_materialization_state",
        ),
        CheckConstraint(
            "(materialization_state = 'materialized' AND application_reaction_id IS NOT NULL) "
            "OR (materialization_state = 'catalog_only' AND application_reaction_id IS NULL)",
            name="ck_catalog_reaction_application_identity",
        ),
        UniqueConstraint("application_reaction_id", name="uq_catalog_reaction_application_id"),
    )

    consolidated_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    application_reaction_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), index=True
    )
    source_package: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name_zh: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    materialization_state: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    not_materialized_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    original_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class CatalogReactionParticipantRow(KnowledgeCatalogBase):
    __tablename__ = "catalog_reaction_participant"

    reaction_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("catalog_reaction.consolidated_id", ondelete="CASCADE"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    coefficient_text: Mapped[str] = mapped_column(String(64), nullable=False)
    species_id: Mapped[str | None] = mapped_column(
        String(200), ForeignKey("catalog_species.consolidated_id", ondelete="RESTRICT"), index=True
    )
    application_target_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), index=True
    )
    target_type: Mapped[str | None] = mapped_column(String(16))
    non_species_ref: Mapped[str | None] = mapped_column(String(240))
    source_species_ref: Mapped[str] = mapped_column(String(240), nullable=False)
    formula_literal: Mapped[str | None] = mapped_column(String(160))
    phase: Mapped[str | None] = mapped_column(String(24))
