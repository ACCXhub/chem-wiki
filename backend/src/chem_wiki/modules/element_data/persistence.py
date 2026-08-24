from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ELEMENT_FIELD_NAMES = (
    "atomic_number",
    "symbol",
    "name_zh",
    "name_en",
    "atomic_weight",
    "group_no",
    "period_no",
    "block",
    "electronegativity",
    "first_ionization_energy",
    "atomic_radius",
)
_ELEMENT_FIELD_VALUES = ", ".join(f"'{name}'" for name in ELEMENT_FIELD_NAMES)


class ElementDataBase(DeclarativeBase):
    pass


class ElementRow(ElementDataBase):
    __tablename__ = "element"
    __table_args__ = (
        CheckConstraint(
            "atomic_number BETWEEN 1 AND 118",
            name="ck_element_atomic_number_1_118",
        ),
        UniqueConstraint("atomic_number", name="uq_element_atomic_number"),
        UniqueConstraint("symbol", name="uq_element_symbol"),
        UniqueConstraint("name_zh", name="uq_element_name_zh"),
        UniqueConstraint("name_en", name="uq_element_name_en"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    atomic_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    symbol: Mapped[str] = mapped_column(String(3), nullable=False)
    name_zh: Mapped[str] = mapped_column(String(16), nullable=False)
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)


class ElementPropertyRow(ElementDataBase):
    __tablename__ = "element_property"
    __table_args__ = (
        CheckConstraint(
            "(atomic_weight_value IS NULL AND atomic_weight_lower IS NULL "
            "AND atomic_weight_upper IS NULL AND atomic_weight_uncertainty IS NULL) "
            "OR (atomic_weight_value IS NOT NULL AND atomic_weight_lower IS NULL "
            "AND atomic_weight_upper IS NULL) "
            "OR (atomic_weight_value IS NULL AND atomic_weight_lower IS NOT NULL "
            "AND atomic_weight_upper IS NOT NULL "
            "AND atomic_weight_lower <= atomic_weight_upper)",
            name="ck_element_property_atomic_weight_shape",
        ),
        CheckConstraint(
            "group_no IS NULL OR group_no BETWEEN 1 AND 18",
            name="ck_element_property_group_no",
        ),
        CheckConstraint(
            "period_no IS NULL OR period_no BETWEEN 1 AND 7",
            name="ck_element_property_period_no",
        ),
        CheckConstraint(
            "block IS NULL OR block IN ('s', 'p', 'd', 'f')",
            name="ck_element_property_block",
        ),
        CheckConstraint(
            "(electronegativity_value IS NULL AND electronegativity_scale IS NULL) "
            "OR (electronegativity_value IS NOT NULL AND electronegativity_scale IS NOT NULL)",
            name="ck_element_property_electronegativity_pair",
        ),
        CheckConstraint(
            "(first_ionization_energy_value IS NULL "
            "AND first_ionization_energy_unit IS NULL) "
            "OR (first_ionization_energy_value IS NOT NULL "
            "AND first_ionization_energy_unit IS NOT NULL)",
            name="ck_element_property_ionization_energy_pair",
        ),
        CheckConstraint(
            "(atomic_radius_value IS NULL AND atomic_radius_unit IS NULL "
            "AND atomic_radius_qualifier IS NULL) "
            "OR (atomic_radius_value IS NOT NULL AND atomic_radius_unit IS NOT NULL "
            "AND atomic_radius_qualifier IS NOT NULL)",
            name="ck_element_property_atomic_radius_group",
        ),
    )

    element_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("element.id", ondelete="CASCADE"),
        primary_key=True,
    )
    atomic_weight_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    atomic_weight_lower: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    atomic_weight_upper: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    atomic_weight_uncertainty: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    group_no: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    period_no: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    block: Mapped[str | None] = mapped_column(String(1), nullable=True)
    electronegativity_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 3), nullable=True)
    electronegativity_scale: Mapped[str | None] = mapped_column(String(32), nullable=True)
    first_ionization_energy_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3), nullable=True
    )
    first_ionization_energy_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    atomic_radius_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    atomic_radius_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    atomic_radius_qualifier: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ElementSourceRow(ElementDataBase):
    __tablename__ = "element_source"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('standard', 'database', 'open_source', 'manual')",
            name="ck_element_source_type",
        ),
        CheckConstraint(
            "reuse_policy IN ('allowed', 'review_required', 'prohibited')",
            name="ck_element_source_reuse_policy",
        ),
        UniqueConstraint("source_key", name="uq_element_source_key"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reuse_policy: Mapped[str] = mapped_column(String(32), nullable=False)


class ElementSourceRecordRow(ElementDataBase):
    __tablename__ = "element_source_record"
    __table_args__ = (
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_element_source_record_content_sha256",
        ),
        UniqueConstraint(
            "source_id",
            "source_version",
            "record_key",
            "content_sha256",
            name="uq_element_source_record_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("element_source.id"), nullable=False
    )
    source_version: Mapped[str] = mapped_column(String(120), nullable=False)
    record_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


class ElementClaimRow(ElementDataBase):
    __tablename__ = "element_claim"
    __table_args__ = (
        CheckConstraint(
            f"field_name IN ({_ELEMENT_FIELD_VALUES})",
            name="ck_element_claim_field_name",
        ),
        CheckConstraint(
            "(normalized_text IS NOT NULL AND normalized_integer IS NULL "
            "AND normalized_numeric IS NULL AND normalized_lower IS NULL "
            "AND normalized_upper IS NULL) "
            "OR (normalized_text IS NULL AND normalized_integer IS NOT NULL "
            "AND normalized_numeric IS NULL AND normalized_lower IS NULL "
            "AND normalized_upper IS NULL) "
            "OR (normalized_text IS NULL AND normalized_integer IS NULL "
            "AND normalized_numeric IS NOT NULL AND normalized_lower IS NULL "
            "AND normalized_upper IS NULL) "
            "OR (normalized_text IS NULL AND normalized_integer IS NULL "
            "AND normalized_numeric IS NULL AND normalized_lower IS NOT NULL "
            "AND normalized_upper IS NOT NULL AND normalized_lower <= normalized_upper)",
            name="ck_element_claim_normalized_value_shape",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_element_claim_verification_status",
        ),
        UniqueConstraint(
            "source_record_id",
            "field_name",
            "transform_version",
            name="uq_element_claim_transformation",
        ),
        UniqueConstraint(
            "id",
            "element_id",
            "field_name",
            name="uq_element_claim_publication_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    element_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("element.id"), nullable=False
    )
    source_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("element_source_record.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_integer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    normalized_numeric: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    normalized_lower: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    normalized_upper: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    canonical_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    uncertainty: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    qualifier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False)
    transform_version: Mapped[str] = mapped_column(String(64), nullable=False)


class ElementPublishedValueRow(ElementDataBase):
    __tablename__ = "element_published_value"
    __table_args__ = (
        CheckConstraint(
            f"field_name IN ({_ELEMENT_FIELD_VALUES})",
            name="ck_element_published_value_field_name",
        ),
        CheckConstraint(
            "selection_method IN ('authority_policy', 'manual')",
            name="ck_element_published_value_selection_method",
        ),
        ForeignKeyConstraint(
            ["claim_id", "element_id", "field_name"],
            ["element_claim.id", "element_claim.element_id", "element_claim.field_name"],
            name="fk_element_published_value_claim",
        ),
    )

    element_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("element.id"),
        primary_key=True,
    )
    field_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    selection_method: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_by: Mapped[str] = mapped_column(String(120), nullable=False)
    selection_reason: Mapped[str] = mapped_column(Text, nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
