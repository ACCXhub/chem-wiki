"""PostgreSQL calibration importer for NIST ASD neutral-atom ionization energies."""

from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from chem_wiki.modules.chemistry_core import AtomicNumber, Element, ElementId, ElementSymbol

from .nist_asd import (
    NIST_ASD_BASE_URL,
    NIST_ASD_CITATION,
    NIST_ASD_TRANSFORM_VERSION,
    NistAsdAdapter,
    NistAsdClaim,
    NistAsdPayloadError,
    NistAsdRawRecord,
)
from .persistence import ElementDataBase

NIST_SOURCE_KEY = "nist-asd-ionization-energies"
NIST_POLICY_VERSION = "m02-nist-asd-v1"


class NistCanonicalElementMissingError(LookupError):
    """Raised when a requested NIST calibration has no canonical Element target."""


class NistCanonicalElementIdentityMismatchError(ValueError):
    """Raised when NIST evidence does not match the existing canonical identity."""


@dataclass(frozen=True, slots=True)
class NistImportResult:
    element_ids: tuple[ElementId, ...]
    source_records_created: int
    claims_created: int
    publications_changed: int


def _load_canonical_elements(
    session: Session,
    atomic_numbers: Collection[int],
) -> tuple[Element, ...]:
    requested = sorted({AtomicNumber(value).value for value in atomic_numbers})
    if not requested:
        return ()

    element_table = ElementDataBase.metadata.tables["element"]
    rows = (
        session.execute(
            select(element_table)
            .where(element_table.c.atomic_number.in_(requested))
            .order_by(element_table.c.atomic_number)
        )
        .mappings()
        .all()
    )
    found = {row["atomic_number"] for row in rows}
    if found != set(requested):
        missing = sorted(set(requested) - found)
        raise NistCanonicalElementMissingError(
            f"NIST cannot create canonical identity; missing atomic_numbers={missing}"
        )
    return tuple(
        Element(
            id=ElementId(row["id"]),
            atomic_number=AtomicNumber(row["atomic_number"]),
            symbol=ElementSymbol(row["symbol"]),
            name_zh=row["name_zh"],
            name_en=row["name_en"],
        )
        for row in rows
    )


def _upsert_source(session: Session) -> UUID:
    source = ElementDataBase.metadata.tables["element_source"]
    values = {
        "title": "NIST Atomic Spectra Database Ionization Energies",
        "publisher": "National Institute of Standards and Technology",
        "source_type": "database",
        "base_url": NIST_ASD_BASE_URL,
        "license_code": None,
        "reuse_policy": "review_required",
    }
    statement = (
        pg_insert(source)
        .values(id=uuid4(), source_key=NIST_SOURCE_KEY, **values)
        .on_conflict_do_update(index_elements=[source.c.source_key], set_=values)
        .returning(source.c.id)
    )
    source_id = session.scalar(statement)
    if source_id is None:  # pragma: no cover - PostgreSQL RETURNING invariant
        raise RuntimeError("NIST ASD source upsert returned no id")
    return source_id


def _upsert_source_record(
    session: Session,
    *,
    source_id: UUID,
    record: NistAsdRawRecord,
) -> tuple[UUID, bool]:
    source_record = ElementDataBase.metadata.tables["element_source_record"]
    statement = (
        pg_insert(source_record)
        .values(
            id=uuid4(),
            source_id=source_id,
            source_version=record.source_version,
            record_key=record.record_key,
            source_url=record.source_url,
            retrieved_at=record.retrieved_at,
            content_sha256=record.content_sha256,
            raw_payload=dict(record.raw_payload),
        )
        .on_conflict_do_nothing(constraint="uq_element_source_record_identity")
        .returning(source_record.c.id)
    )
    inserted_id = session.scalar(statement)
    if inserted_id is not None:
        return inserted_id, True

    existing_id = session.scalar(
        select(source_record.c.id).where(
            source_record.c.source_id == source_id,
            source_record.c.source_version == record.source_version,
            source_record.c.record_key == record.record_key,
            source_record.c.content_sha256 == record.content_sha256,
        )
    )
    if existing_id is None:  # pragma: no cover - conflict target invariant
        raise RuntimeError("NIST ASD source record conflict returned no existing row")
    return existing_id, False


def _upsert_claim(
    session: Session,
    *,
    element_id: UUID,
    source_record_id: UUID,
    claim: NistAsdClaim,
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
            normalized_numeric=claim.normalized_numeric,
            canonical_unit=claim.canonical_unit,
            uncertainty=claim.uncertainty,
            qualifier=claim.qualifier,
            verification_status="verified",
            transform_version=NIST_ASD_TRANSFORM_VERSION,
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
            claim_table.c.transform_version == NIST_ASD_TRANSFORM_VERSION,
        )
    )
    if existing_id is None:  # pragma: no cover - conflict target invariant
        raise RuntimeError("NIST ASD claim conflict returned no existing row")
    return existing_id, False


def _publish_claim(
    session: Session,
    *,
    element_id: UUID,
    claim_id: UUID,
    claim: NistAsdClaim,
    record: NistAsdRawRecord,
) -> bool:
    published = ElementDataBase.metadata.tables["element_published_value"]
    current_claim_id = session.scalar(
        select(published.c.claim_id).where(
            published.c.element_id == element_id,
            published.c.field_name == "first_ionization_energy",
        )
    )
    if current_claim_id == claim_id:
        return False

    property_table = ElementDataBase.metadata.tables["element_property"]
    property_values = {
        "first_ionization_energy_value": claim.normalized_numeric,
        "first_ionization_energy_unit": claim.canonical_unit,
    }
    session.execute(
        pg_insert(property_table)
        .values(element_id=element_id, **property_values)
        .on_conflict_do_update(
            index_elements=[property_table.c.element_id],
            set_=property_values,
        )
    )
    publication_values = {
        "claim_id": claim_id,
        "selection_method": "authority_policy",
        "policy_version": NIST_POLICY_VERSION,
        "selected_by": f"policy:{NIST_POLICY_VERSION}",
        "selection_reason": (
            "NIST ASD critically evaluated neutral-atom first ionization energy "
            f"calibrates supplemental values; citation: {NIST_ASD_CITATION}"
        ),
        "selected_at": record.retrieved_at,
    }
    session.execute(
        pg_insert(published)
        .values(
            element_id=element_id,
            field_name="first_ionization_energy",
            **publication_values,
        )
        .on_conflict_do_update(
            index_elements=[published.c.element_id, published.c.field_name],
            set_=publication_values,
        )
    )
    return True


def _persist_nist_records(
    session: Session,
    records: tuple[NistAsdRawRecord, ...],
    elements: tuple[Element, ...],
) -> NistImportResult:
    elements_by_number = {element.atomic_number.value: element for element in elements}
    for record in records:
        canonical = elements_by_number[record.atomic_number]
        if canonical.symbol.value != record.symbol:
            raise NistCanonicalElementIdentityMismatchError(
                f"NIST ASD identity conflicts with canonical atomic_number={record.atomic_number}"
            )

    if not records:
        return NistImportResult((), 0, 0, 0)

    source_id = _upsert_source(session)
    source_records_created = 0
    claims_created = 0
    publications_changed = 0

    for record in sorted(records, key=lambda item: item.atomic_number):
        element = elements_by_number[record.atomic_number]
        source_record_id, source_record_created = _upsert_source_record(
            session,
            source_id=source_id,
            record=record,
        )
        source_records_created += int(source_record_created)
        claim = NistAsdAdapter.normalize(record)
        claim_id, claim_created = _upsert_claim(
            session,
            element_id=element.id.value,
            source_record_id=source_record_id,
            claim=claim,
        )
        claims_created += int(claim_created)
        publications_changed += int(
            _publish_claim(
                session,
                element_id=element.id.value,
                claim_id=claim_id,
                claim=claim,
                record=record,
            )
        )

    return NistImportResult(
        element_ids=tuple(element.id for element in elements),
        source_records_created=source_records_created,
        claims_created=claims_created,
        publications_changed=publications_changed,
    )


def import_nist_records(
    session: Session,
    records: Collection[NistAsdRawRecord],
) -> NistImportResult:
    """Persist and publish normalized NIST ASD calibration evidence."""

    stable_records = tuple(records)
    atomic_numbers: list[int] = []
    seen: set[int] = set()
    for record in stable_records:
        if record.atomic_number in seen:
            raise ValueError(f"duplicate NIST ASD atomic_number={record.atomic_number}")
        seen.add(record.atomic_number)
        atomic_numbers.append(record.atomic_number)
    elements = _load_canonical_elements(session, atomic_numbers)
    return _persist_nist_records(session, stable_records, elements)


def import_nist_calibrations(
    session: Session,
    *,
    adapter: NistAsdAdapter,
    atomic_numbers: Collection[int],
) -> NistImportResult:
    """Fetch NIST evidence for existing canonical Elements and apply calibration."""

    elements = _load_canonical_elements(session, atomic_numbers)
    records = adapter.fetch_neutral_atoms({element.symbol.value for element in elements})
    requested = {element.atomic_number.value for element in elements}
    returned = {record.atomic_number for record in records}
    if returned != requested:
        raise NistAsdPayloadError(
            f"NIST ASD returned atomic_numbers={sorted(returned)}; expected={sorted(requested)}"
        )
    return _persist_nist_records(session, records, elements)
