"""Create the M02 element persistence baseline.

Revision ID: 20260820_01
Revises:
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260820_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ELEMENT_FIELD_VALUES = (
    "'atomic_number', 'symbol', 'name_zh', 'name_en', 'atomic_weight', "
    "'group_no', 'period_no', 'block', 'electronegativity', "
    "'first_ionization_energy', 'atomic_radius'"
)


def upgrade() -> None:
    op.create_table(
        "element",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("atomic_number", sa.SmallInteger(), nullable=False),
        sa.Column("symbol", sa.String(length=3), nullable=False),
        sa.Column("name_zh", sa.String(length=16), nullable=False),
        sa.Column("name_en", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "atomic_number BETWEEN 1 AND 118",
            name="ck_element_atomic_number_1_118",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_element"),
        sa.UniqueConstraint("atomic_number", name="uq_element_atomic_number"),
        sa.UniqueConstraint("symbol", name="uq_element_symbol"),
        sa.UniqueConstraint("name_zh", name="uq_element_name_zh"),
        sa.UniqueConstraint("name_en", name="uq_element_name_en"),
    )
    op.create_table(
        "element_property",
        sa.Column("element_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("atomic_weight_value", sa.Numeric(), nullable=True),
        sa.Column("atomic_weight_lower", sa.Numeric(), nullable=True),
        sa.Column("atomic_weight_upper", sa.Numeric(), nullable=True),
        sa.Column("atomic_weight_uncertainty", sa.Numeric(), nullable=True),
        sa.Column("group_no", sa.SmallInteger(), nullable=True),
        sa.Column("period_no", sa.SmallInteger(), nullable=True),
        sa.Column("block", sa.String(length=1), nullable=True),
        sa.Column("electronegativity_value", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("electronegativity_scale", sa.String(length=32), nullable=True),
        sa.Column(
            "first_ionization_energy_value",
            sa.Numeric(precision=10, scale=3),
            nullable=True,
        ),
        sa.Column("first_ionization_energy_unit", sa.String(length=24), nullable=True),
        sa.Column("atomic_radius_value", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("atomic_radius_unit", sa.String(length=24), nullable=True),
        sa.Column("atomic_radius_qualifier", sa.String(length=32), nullable=True),
        sa.CheckConstraint(
            "(atomic_weight_value IS NULL AND atomic_weight_lower IS NULL "
            "AND atomic_weight_upper IS NULL AND atomic_weight_uncertainty IS NULL) "
            "OR (atomic_weight_value IS NOT NULL AND atomic_weight_lower IS NULL "
            "AND atomic_weight_upper IS NULL) "
            "OR (atomic_weight_value IS NULL AND atomic_weight_lower IS NOT NULL "
            "AND atomic_weight_upper IS NOT NULL "
            "AND atomic_weight_lower <= atomic_weight_upper)",
            name="ck_element_property_atomic_weight_shape",
        ),
        sa.CheckConstraint(
            "group_no IS NULL OR group_no BETWEEN 1 AND 18",
            name="ck_element_property_group_no",
        ),
        sa.CheckConstraint(
            "period_no IS NULL OR period_no BETWEEN 1 AND 7",
            name="ck_element_property_period_no",
        ),
        sa.CheckConstraint(
            "block IS NULL OR block IN ('s', 'p', 'd', 'f')",
            name="ck_element_property_block",
        ),
        sa.CheckConstraint(
            "(electronegativity_value IS NULL AND electronegativity_scale IS NULL) "
            "OR (electronegativity_value IS NOT NULL AND electronegativity_scale IS NOT NULL)",
            name="ck_element_property_electronegativity_pair",
        ),
        sa.CheckConstraint(
            "(first_ionization_energy_value IS NULL "
            "AND first_ionization_energy_unit IS NULL) "
            "OR (first_ionization_energy_value IS NOT NULL "
            "AND first_ionization_energy_unit IS NOT NULL)",
            name="ck_element_property_ionization_energy_pair",
        ),
        sa.CheckConstraint(
            "(atomic_radius_value IS NULL AND atomic_radius_unit IS NULL "
            "AND atomic_radius_qualifier IS NULL) "
            "OR (atomic_radius_value IS NOT NULL AND atomic_radius_unit IS NOT NULL "
            "AND atomic_radius_qualifier IS NOT NULL)",
            name="ck_element_property_atomic_radius_group",
        ),
        sa.ForeignKeyConstraint(
            ["element_id"],
            ["element.id"],
            name="fk_element_property_element",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("element_id", name="pk_element_property"),
    )
    op.create_table(
        "element_source",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("publisher", sa.String(length=160), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("license_code", sa.String(length=80), nullable=True),
        sa.Column("reuse_policy", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('standard', 'database', 'open_source', 'manual')",
            name="ck_element_source_type",
        ),
        sa.CheckConstraint(
            "reuse_policy IN ('allowed', 'review_required', 'prohibited')",
            name="ck_element_source_reuse_policy",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_element_source"),
        sa.UniqueConstraint("source_key", name="uq_element_source_key"),
    )
    op.create_table(
        "element_source_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_version", sa.String(length=120), nullable=False),
        sa.Column("record_key", sa.String(length=160), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_element_source_record_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["element_source.id"],
            name="fk_element_source_record_source",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_element_source_record"),
        sa.UniqueConstraint(
            "source_id",
            "source_version",
            "record_key",
            "content_sha256",
            name="uq_element_source_record_identity",
        ),
    )
    op.create_table(
        "element_claim",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("element_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("normalized_integer", sa.Integer(), nullable=True),
        sa.Column("normalized_numeric", sa.Numeric(), nullable=True),
        sa.Column("normalized_lower", sa.Numeric(), nullable=True),
        sa.Column("normalized_upper", sa.Numeric(), nullable=True),
        sa.Column("canonical_unit", sa.String(length=24), nullable=True),
        sa.Column("uncertainty", sa.Numeric(), nullable=True),
        sa.Column("qualifier", sa.String(length=64), nullable=True),
        sa.Column("verification_status", sa.String(length=16), nullable=False),
        sa.Column("transform_version", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"field_name IN ({ELEMENT_FIELD_VALUES})",
            name="ck_element_claim_field_name",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_element_claim_verification_status",
        ),
        sa.ForeignKeyConstraint(
            ["element_id"],
            ["element.id"],
            name="fk_element_claim_element",
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["element_source_record.id"],
            name="fk_element_claim_source_record",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_element_claim"),
        sa.UniqueConstraint(
            "source_record_id",
            "field_name",
            "transform_version",
            name="uq_element_claim_transformation",
        ),
        sa.UniqueConstraint(
            "id",
            "element_id",
            "field_name",
            name="uq_element_claim_publication_target",
        ),
    )
    op.create_table(
        "element_published_value",
        sa.Column("element_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selection_method", sa.String(length=16), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("selected_by", sa.String(length=120), nullable=False),
        sa.Column("selection_reason", sa.Text(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"field_name IN ({ELEMENT_FIELD_VALUES})",
            name="ck_element_published_value_field_name",
        ),
        sa.CheckConstraint(
            "selection_method IN ('authority_policy', 'manual')",
            name="ck_element_published_value_selection_method",
        ),
        sa.ForeignKeyConstraint(
            ["element_id"],
            ["element.id"],
            name="fk_element_published_value_element",
        ),
        sa.ForeignKeyConstraint(
            ["claim_id", "element_id", "field_name"],
            ["element_claim.id", "element_claim.element_id", "element_claim.field_name"],
            name="fk_element_published_value_claim",
        ),
        sa.PrimaryKeyConstraint(
            "element_id",
            "field_name",
            name="pk_element_published_value",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION m02_check_element_publication_integrity()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            target_element_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'element' THEN
                target_element_id := COALESCE(NEW.id, OLD.id);
            ELSE
                target_element_id := COALESCE(NEW.element_id, OLD.element_id);
            END IF;

            IF NOT EXISTS (SELECT 1 FROM element WHERE id = target_element_id) THEN
                RETURN NULL;
            END IF;

            IF (
                SELECT count(*)
                FROM element_published_value
                WHERE element_id = target_element_id
                  AND field_name IN ('atomic_number', 'symbol', 'name_zh', 'name_en')
            ) <> 4 THEN
                RAISE EXCEPTION
                    'element % must publish atomic_number, symbol, name_zh, and name_en',
                    target_element_id;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM element e
                JOIN element_published_value published
                  ON published.element_id = e.id
                JOIN element_claim claim
                  ON claim.id = published.claim_id
                 AND claim.element_id = published.element_id
                 AND claim.field_name = published.field_name
                WHERE e.id = target_element_id
                  AND (
                    (published.field_name = 'atomic_number'
                     AND claim.normalized_integer IS DISTINCT FROM e.atomic_number)
                    OR (published.field_name = 'symbol'
                        AND claim.normalized_text IS DISTINCT FROM e.symbol)
                    OR (published.field_name = 'name_zh'
                        AND claim.normalized_text IS DISTINCT FROM e.name_zh)
                    OR (published.field_name = 'name_en'
                        AND claim.normalized_text IS DISTINCT FROM e.name_en)
                  )
            ) THEN
                RAISE EXCEPTION
                    'element % canonical identity does not match its published claim',
                    target_element_id;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM element_property property
                WHERE property.element_id = target_element_id
                  AND (
                    ((property.atomic_weight_value IS NOT NULL
                      OR property.atomic_weight_lower IS NOT NULL)
                     AND NOT EXISTS (
                        SELECT 1 FROM element_published_value
                        WHERE element_id = target_element_id
                          AND field_name = 'atomic_weight'
                     ))
                    OR (property.group_no IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM element_published_value
                        WHERE element_id = target_element_id AND field_name = 'group_no'
                    ))
                    OR (property.period_no IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM element_published_value
                        WHERE element_id = target_element_id AND field_name = 'period_no'
                    ))
                    OR (property.block IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM element_published_value
                        WHERE element_id = target_element_id AND field_name = 'block'
                    ))
                    OR (property.electronegativity_value IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM element_published_value
                        WHERE element_id = target_element_id
                          AND field_name = 'electronegativity'
                    ))
                    OR (property.first_ionization_energy_value IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM element_published_value
                        WHERE element_id = target_element_id
                          AND field_name = 'first_ionization_energy'
                    ))
                    OR (property.atomic_radius_value IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM element_published_value
                        WHERE element_id = target_element_id AND field_name = 'atomic_radius'
                    ))
                  )
            ) THEN
                RAISE EXCEPTION
                    'element % has a canonical property without a published claim',
                    target_element_id;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM element_published_value published
                JOIN element_claim claim
                  ON claim.id = published.claim_id
                 AND claim.element_id = published.element_id
                 AND claim.field_name = published.field_name
                LEFT JOIN element_property property
                  ON property.element_id = published.element_id
                WHERE published.element_id = target_element_id
                  AND published.field_name IN (
                    'atomic_weight', 'group_no', 'period_no', 'block',
                    'electronegativity', 'first_ionization_energy', 'atomic_radius'
                  )
                  AND (
                    property.element_id IS NULL
                    OR (published.field_name = 'atomic_weight' AND NOT (
                        (
                            property.atomic_weight_value IS NOT NULL
                            AND claim.normalized_numeric
                                IS NOT DISTINCT FROM property.atomic_weight_value
                            AND claim.normalized_lower IS NULL
                            AND claim.normalized_upper IS NULL
                            AND claim.uncertainty
                                IS NOT DISTINCT FROM property.atomic_weight_uncertainty
                        )
                        OR (
                            property.atomic_weight_value IS NULL
                            AND property.atomic_weight_lower IS NOT NULL
                            AND claim.normalized_numeric IS NULL
                            AND claim.normalized_lower
                                IS NOT DISTINCT FROM property.atomic_weight_lower
                            AND claim.normalized_upper
                                IS NOT DISTINCT FROM property.atomic_weight_upper
                            AND claim.uncertainty
                                IS NOT DISTINCT FROM property.atomic_weight_uncertainty
                        )
                    ))
                    OR (published.field_name = 'group_no'
                        AND claim.normalized_integer IS DISTINCT FROM property.group_no)
                    OR (published.field_name = 'period_no'
                        AND claim.normalized_integer IS DISTINCT FROM property.period_no)
                    OR (published.field_name = 'block'
                        AND claim.normalized_text IS DISTINCT FROM property.block)
                    OR (published.field_name = 'electronegativity' AND (
                        claim.normalized_numeric
                            IS DISTINCT FROM property.electronegativity_value
                        OR claim.qualifier
                            IS DISTINCT FROM property.electronegativity_scale
                    ))
                    OR (published.field_name = 'first_ionization_energy' AND (
                        claim.normalized_numeric::numeric(10, 3)
                            IS DISTINCT FROM property.first_ionization_energy_value
                        OR claim.canonical_unit
                            IS DISTINCT FROM property.first_ionization_energy_unit
                    ))
                    OR (published.field_name = 'atomic_radius' AND (
                        claim.normalized_numeric IS DISTINCT FROM property.atomic_radius_value
                        OR claim.canonical_unit IS DISTINCT FROM property.atomic_radius_unit
                        OR claim.qualifier IS DISTINCT FROM property.atomic_radius_qualifier
                    ))
                  )
            ) THEN
                RAISE EXCEPTION
                    'element % canonical property does not match its published claim',
                    target_element_id;
            END IF;

            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_element_publication_integrity
        AFTER INSERT OR UPDATE ON element
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION m02_check_element_publication_integrity()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_element_property_publication_integrity
        AFTER INSERT OR UPDATE OR DELETE ON element_property
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION m02_check_element_publication_integrity()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_element_published_value_integrity
        AFTER INSERT OR UPDATE OR DELETE ON element_published_value
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION m02_check_element_publication_integrity()
        """
    )
    op.execute(
        """
        CREATE FUNCTION m02_reject_immutable_evidence()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION '% evidence is immutable', TG_TABLE_NAME;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_element_source_record_immutable
        BEFORE UPDATE OR DELETE ON element_source_record
        FOR EACH ROW EXECUTE FUNCTION m02_reject_immutable_evidence()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_element_claim_immutable
        BEFORE UPDATE OR DELETE ON element_claim
        FOR EACH ROW EXECUTE FUNCTION m02_reject_immutable_evidence()
        """
    )
    op.execute(
        """
        CREATE FUNCTION m02_reject_element_identity_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.atomic_number IS DISTINCT FROM OLD.atomic_number THEN
                RAISE EXCEPTION 'element id and atomic_number are immutable';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_element_identity_immutable
        BEFORE UPDATE ON element
        FOR EACH ROW EXECUTE FUNCTION m02_reject_element_identity_change()
        """
    )
    op.execute(
        """
        CREATE FUNCTION m02_reject_source_key_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.source_key IS DISTINCT FROM OLD.source_key THEN
                RAISE EXCEPTION 'element source_key is immutable';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_element_source_key_immutable
        BEFORE UPDATE ON element_source
        FOR EACH ROW EXECUTE FUNCTION m02_reject_source_key_change()
        """
    )
    op.execute(
        """
        CREATE FUNCTION m02_check_source_payload_policy()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            target_source_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'element_source' THEN
                target_source_id := NEW.id;
            ELSE
                target_source_id := NEW.source_id;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM element_source source
                JOIN element_source_record record ON record.source_id = source.id
                WHERE source.id = target_source_id
                  AND source.reuse_policy = 'prohibited'
                  AND record.raw_payload IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'source % prohibits retaining raw payload',
                    target_source_id;
            END IF;
            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_element_source_payload_policy
        AFTER INSERT OR UPDATE ON element_source
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION m02_check_source_payload_policy()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_element_source_record_payload_policy
        AFTER INSERT ON element_source_record
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION m02_check_source_payload_policy()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_element_source_record_payload_policy ON element_source_record")
    op.execute("DROP TRIGGER trg_element_source_payload_policy ON element_source")
    op.execute("DROP FUNCTION m02_check_source_payload_policy()")
    op.execute("DROP TRIGGER trg_element_source_key_immutable ON element_source")
    op.execute("DROP FUNCTION m02_reject_source_key_change()")
    op.execute("DROP TRIGGER trg_element_identity_immutable ON element")
    op.execute("DROP FUNCTION m02_reject_element_identity_change()")
    op.execute("DROP TRIGGER trg_element_claim_immutable ON element_claim")
    op.execute("DROP TRIGGER trg_element_source_record_immutable ON element_source_record")
    op.execute("DROP FUNCTION m02_reject_immutable_evidence()")
    op.execute("DROP TRIGGER trg_element_published_value_integrity ON element_published_value")
    op.execute("DROP TRIGGER trg_element_property_publication_integrity ON element_property")
    op.execute("DROP TRIGGER trg_element_publication_integrity ON element")
    op.execute("DROP FUNCTION m02_check_element_publication_integrity()")
    op.drop_table("element_published_value")
    op.drop_table("element_claim")
    op.drop_table("element_source_record")
    op.drop_table("element_source")
    op.drop_table("element_property")
    op.drop_table("element")
