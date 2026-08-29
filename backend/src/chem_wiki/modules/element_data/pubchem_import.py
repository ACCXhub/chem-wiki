"""Narrow PostgreSQL importer for normalized PubChem element evidence."""

from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from chem_wiki.modules.chemistry_core import (
    AtomicNumber,
    Element,
    ElementId,
    ElementSymbol,
)

from .persistence import ElementDataBase
from .pubchem import (
    PUBCHEM_CITATION_URL,
    PUBCHEM_TRANSFORM_VERSION,
    NormalizedClaim,
    NormalizedElementRecord,
    PubChemAdapter,
)

PUBCHEM_SOURCE_KEY = "pubchem-periodic-table"
PUBCHEM_POLICY_VERSION = "m02-pubchem-v1"
_PUBCHEM_ENGLISH_NAME_VARIANTS = {
    13: frozenset({"aluminium", "aluminum"}),
    55: frozenset({"caesium", "cesium"}),
}


class CanonicalElementMissingError(LookupError):
    """Raised when PubChem supplemental evidence has no canonical target."""


class CanonicalElementIdentityMismatchError(ValueError):
    """Raised when PubChem identity evidence conflicts with the canonical element."""


@dataclass(frozen=True, slots=True)
class PubChemImportResult:
    element_ids: tuple[ElementId, ...]
    source_records_created: int
    claims_created: int
    publications_changed: int


def _load_canonical_element(
    session: Session,
    record: NormalizedElementRecord,
) -> Element:
    element_table = ElementDataBase.metadata.tables["element"]
    row = (
        session.execute(
            select(element_table).where(element_table.c.atomic_number == record.atomic_number)
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise CanonicalElementMissingError(
            "PubChem cannot create canonical identity; "
            f"no element exists for atomic_number={record.atomic_number}"
        )

    canonical = Element(
        id=ElementId(row["id"]),
        atomic_number=AtomicNumber(row["atomic_number"]),
        symbol=ElementSymbol(row["symbol"]),
        name_zh=row["name_zh"],
        name_en=row["name_en"],
    )
    accepted_names = _PUBCHEM_ENGLISH_NAME_VARIANTS.get(
        record.atomic_number,
        frozenset({canonical.name_en.casefold()}),
    )
    if canonical.symbol.value != record.symbol or record.name_en.casefold() not in accepted_names:
        raise CanonicalElementIdentityMismatchError(
            f"PubChem identity conflicts with canonical atomic_number={record.atomic_number}"
        )
    return canonical


def _upsert_source(session: Session) -> UUID:
    source = ElementDataBase.metadata.tables["element_source"]
    statement = (
        pg_insert(source)
        .values(
            id=uuid4(),
            source_key=PUBCHEM_SOURCE_KEY,
            title="PubChem Periodic Table",
            publisher="National Center for Biotechnology Information",
            source_type="database",
            base_url="https://pubchem.ncbi.nlm.nih.gov/periodic-table/",
            license_code=None,
            reuse_policy="review_required",
        )
        .on_conflict_do_update(
            index_elements=[source.c.source_key],
            set_={
                "title": "PubChem Periodic Table",
                "publisher": "National Center for Biotechnology Information",
                "source_type": "database",
                "base_url": "https://pubchem.ncbi.nlm.nih.gov/periodic-table/",
                "license_code": None,
                "reuse_policy": "review_required",
            },
        )
        .returning(source.c.id)
    )
    source_id = session.scalar(statement)
    if source_id is None:  # pragma: no cover - PostgreSQL RETURNING invariant
        raise RuntimeError("PubChem source upsert returned no id")
    return source_id


def _upsert_source_record(
    session: Session,
    source_id: UUID,
    record: NormalizedElementRecord,
) -> tuple[UUID, bool]:
    source_record = ElementDataBase.metadata.tables["element_source_record"]
    raw = record.raw_record
    statement = (
        pg_insert(source_record)
        .values(
            id=uuid4(),
            source_id=source_id,
            source_version=raw.source_version,
            record_key=raw.record_key,
            source_url=raw.source_url,
            retrieved_at=raw.retrieved_at,
            content_sha256=raw.content_sha256,
            raw_payload=dict(raw.raw_payload),
        )
        .on_conflict_do_nothing(
            constraint="uq_element_source_record_identity",
        )
        .returning(source_record.c.id)
    )
    inserted_id = session.scalar(statement)
    if inserted_id is not None:
        return inserted_id, True

    existing_id = session.scalar(
        select(source_record.c.id).where(
            source_record.c.source_id == source_id,
            source_record.c.source_version == raw.source_version,
            source_record.c.record_key == raw.record_key,
            source_record.c.content_sha256 == raw.content_sha256,
        )
    )
    if existing_id is None:  # pragma: no cover - conflict target invariant
        raise RuntimeError("PubChem source record conflict returned no existing row")
    return existing_id, False


def _upsert_claim(
    session: Session,
    *,
    element_id: UUID,
    source_record_id: UUID,
    claim: NormalizedClaim,
) -> tuple[UUID, bool]:
    claim_table = ElementDataBase.metadata.tables["element_claim"]
    statement = (
        pg_insert(claim_table)
        .values(
            id=uuid4(),
            element_id=element_id,
            source_record_id=source_record_id,
            field_name=claim.field_name,
            raw_value=claim.raw_value,
            normalized_text=claim.normalized_text,
            normalized_integer=claim.normalized_integer,
            normalized_numeric=claim.normalized_numeric,
            canonical_unit=claim.canonical_unit,
            qualifier=claim.qualifier,
            verification_status="verified",
            transform_version=PUBCHEM_TRANSFORM_VERSION,
        )
        .on_conflict_do_nothing(constraint="uq_element_claim_transformation")
        .returning(claim_table.c.id)
    )
    inserted_id = session.scalar(statement)
    if inserted_id is not None:
        return inserted_id, True

    existing_id = session.scalar(
        select(claim_table.c.id).where(
            claim_table.c.source_record_id == source_record_id,
            claim_table.c.field_name == claim.field_name,
            claim_table.c.transform_version == PUBCHEM_TRANSFORM_VERSION,
        )
    )
    if existing_id is None:  # pragma: no cover - conflict target invariant
        raise RuntimeError("PubChem claim conflict returned no existing row")
    return existing_id, False


def _property_values(claim: NormalizedClaim) -> dict[str, object]:
    if claim.normalized_numeric is None:
        raise ValueError(f"published PubChem claim {claim.field_name} must be numeric")
    if claim.field_name == "electronegativity":
        return {
            "electronegativity_value": claim.normalized_numeric,
            "electronegativity_scale": claim.qualifier,
        }
    if claim.field_name == "first_ionization_energy":
        return {
            "first_ionization_energy_value": claim.normalized_numeric,
            "first_ionization_energy_unit": claim.canonical_unit,
        }
    if claim.field_name == "atomic_radius":
        return {
            "atomic_radius_value": claim.normalized_numeric,
            "atomic_radius_unit": claim.canonical_unit,
            "atomic_radius_qualifier": claim.qualifier,
        }
    raise ValueError(f"field is not publishable from PubChem: {claim.field_name}")


def _publish_claim(
    session: Session,
    *,
    element_id: UUID,
    claim_id: UUID,
    claim: NormalizedClaim,
    record: NormalizedElementRecord,
) -> bool:
    published = ElementDataBase.metadata.tables["element_published_value"]
    claim_table = ElementDataBase.metadata.tables["element_claim"]
    source_record = ElementDataBase.metadata.tables["element_source_record"]
    source = ElementDataBase.metadata.tables["element_source"]
    current_source_key = session.scalar(
        select(source.c.source_key)
        .select_from(published)
        .join(claim_table, claim_table.c.id == published.c.claim_id)
        .join(source_record, source_record.c.id == claim_table.c.source_record_id)
        .join(source, source.c.id == source_record.c.source_id)
        .where(
            published.c.element_id == element_id,
            published.c.field_name == claim.field_name,
        )
    )
    if claim.field_name == "first_ionization_energy" and current_source_key == (
        "nist-asd-ionization-energies"
    ):
        return False
    current_claim_id = session.scalar(
        select(published.c.claim_id).where(
            published.c.element_id == element_id,
            published.c.field_name == claim.field_name,
        )
    )
    if current_claim_id == claim_id:
        return False

    property_table = ElementDataBase.metadata.tables["element_property"]
    property_values = _property_values(claim)
    session.execute(
        pg_insert(property_table)
        .values(element_id=element_id, **property_values)
        .on_conflict_do_update(
            index_elements=[property_table.c.element_id],
            set_=property_values,
        )
    )
    session.execute(
        pg_insert(published)
        .values(
            element_id=element_id,
            field_name=claim.field_name,
            claim_id=claim_id,
            selection_method="authority_policy",
            policy_version=PUBCHEM_POLICY_VERSION,
            selected_by=f"policy:{PUBCHEM_POLICY_VERSION}",
            selection_reason=(
                "PubChem supplemental property selected under M02 policy; "
                f"citation: {PUBCHEM_CITATION_URL}"
            ),
            selected_at=record.raw_record.retrieved_at,
        )
        .on_conflict_do_update(
            index_elements=[published.c.element_id, published.c.field_name],
            set_={
                "claim_id": claim_id,
                "selection_method": "authority_policy",
                "policy_version": PUBCHEM_POLICY_VERSION,
                "selected_by": f"policy:{PUBCHEM_POLICY_VERSION}",
                "selection_reason": (
                    "PubChem supplemental property selected under M02 policy; "
                    f"citation: {PUBCHEM_CITATION_URL}"
                ),
                "selected_at": record.raw_record.retrieved_at,
            },
        )
    )
    return True


def import_pubchem_records(
    session: Session,
    records: list[NormalizedElementRecord] | tuple[NormalizedElementRecord, ...],
) -> PubChemImportResult:
    """Persist PubChem evidence and publish allowed fields in the caller's transaction."""

    canonical_by_atomic_number: dict[int, Element] = {}
    for record in records:
        if record.atomic_number in canonical_by_atomic_number:
            raise ValueError(f"duplicate PubChem atomic_number={record.atomic_number}")
        canonical_by_atomic_number[record.atomic_number] = _load_canonical_element(session, record)

    if not records:
        return PubChemImportResult((), 0, 0, 0)

    source_id = _upsert_source(session)
    source_records_created = 0
    claims_created = 0
    publications_changed = 0
    element_ids: list[ElementId] = []

    for record in records:
        canonical = canonical_by_atomic_number[record.atomic_number]
        element_ids.append(canonical.id)
        source_record_id, source_record_created = _upsert_source_record(
            session,
            source_id,
            record,
        )
        source_records_created += int(source_record_created)

        for claim in record.claims:
            claim_id, claim_created = _upsert_claim(
                session,
                element_id=canonical.id.value,
                source_record_id=source_record_id,
                claim=claim,
            )
            claims_created += int(claim_created)
            if claim.field_name in record.publishable_fields:
                publications_changed += int(
                    _publish_claim(
                        session,
                        element_id=canonical.id.value,
                        claim_id=claim_id,
                        claim=claim,
                        record=record,
                    )
                )

    return PubChemImportResult(
        element_ids=tuple(element_ids),
        source_records_created=source_records_created,
        claims_created=claims_created,
        publications_changed=publications_changed,
    )


def import_pubchem_elements(
    session: Session,
    *,
    adapter: PubChemAdapter,
    atomic_numbers: Collection[int],
) -> PubChemImportResult:
    """Run the PubChem adapter-to-PostgreSQL vertical slice."""

    raw_records = adapter.fetch_elements(atomic_numbers)
    normalized_records = tuple(adapter.normalize(record) for record in raw_records)
    return import_pubchem_records(session, normalized_records)
