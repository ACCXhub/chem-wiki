"""Narrow PostgreSQL bootstrap for the frozen M02 Element identity composition."""

from dataclasses import dataclass
from datetime import datetime
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

from .iupac import (
    IUPAC_PUBLISHER,
    IUPAC_REUSE_POLICY,
    IUPAC_SOURCE_KEY,
    IUPAC_SOURCE_TITLE,
    IUPAC_SOURCE_TYPE,
    IUPAC_TRANSFORM_VERSION,
    IupacElementRecord,
    load_iupac_elements,
)
from .official_chinese_names import (
    OFFICIAL_CHINESE_PUBLISHER,
    OFFICIAL_CHINESE_REUSE_POLICY,
    OFFICIAL_CHINESE_SOURCE_KEY,
    OFFICIAL_CHINESE_SOURCE_TITLE,
    OFFICIAL_CHINESE_SOURCE_TYPE,
    OFFICIAL_CHINESE_TRANSFORM_VERSION,
    OfficialChineseNameRecord,
    load_official_chinese_names,
)
from .periodic_table_pro import (
    PERIODIC_TABLE_PRO_PUBLISHER,
    PERIODIC_TABLE_PRO_REUSE_POLICY,
    PERIODIC_TABLE_PRO_SOURCE_KEY,
    PERIODIC_TABLE_PRO_SOURCE_TITLE,
    PERIODIC_TABLE_PRO_SOURCE_TYPE,
    PERIODIC_TABLE_PRO_TRANSFORM_VERSION,
    PeriodicTableProNameRecord,
    load_periodic_table_pro_names,
)
from .persistence import ElementDataBase

IDENTITY_POLICY_VERSION = "m02-element-identity-v1"


class IdentityCompositionError(ValueError):
    """Raised before persistence when the three frozen sources cannot form 118 identities."""


@dataclass(frozen=True, slots=True)
class IdentityBootstrapResult:
    element_ids: tuple[ElementId, ...]
    elements_created: int
    source_records_created: int
    claims_created: int
    publications_changed: int


@dataclass(frozen=True, slots=True)
class _SourceDefinition:
    source_key: str
    title: str
    publisher: str
    source_type: str
    base_url: str
    reuse_policy: str


@dataclass(frozen=True, slots=True)
class _IdentityInput:
    iupac: IupacElementRecord
    chinese: PeriodicTableProNameRecord | OfficialChineseNameRecord


_IdentitySourceRecord = IupacElementRecord | PeriodicTableProNameRecord | OfficialChineseNameRecord


_IUPAC_SOURCE = _SourceDefinition(
    source_key=IUPAC_SOURCE_KEY,
    title=IUPAC_SOURCE_TITLE,
    publisher=IUPAC_PUBLISHER,
    source_type=IUPAC_SOURCE_TYPE,
    base_url="https://iupac.org/what-we-do/periodic-table-of-elements/",
    reuse_policy=IUPAC_REUSE_POLICY,
)
_PERIODIC_TABLE_PRO_SOURCE = _SourceDefinition(
    source_key=PERIODIC_TABLE_PRO_SOURCE_KEY,
    title=PERIODIC_TABLE_PRO_SOURCE_TITLE,
    publisher=PERIODIC_TABLE_PRO_PUBLISHER,
    source_type=PERIODIC_TABLE_PRO_SOURCE_TYPE,
    base_url="https://github.com/baotlake/periodic-table-pro",
    reuse_policy=PERIODIC_TABLE_PRO_REUSE_POLICY,
)
_OFFICIAL_CHINESE_SOURCE = _SourceDefinition(
    source_key=OFFICIAL_CHINESE_SOURCE_KEY,
    title=OFFICIAL_CHINESE_SOURCE_TITLE,
    publisher=OFFICIAL_CHINESE_PUBLISHER,
    source_type=OFFICIAL_CHINESE_SOURCE_TYPE,
    base_url="http://www.cnterm.cn/",
    reuse_policy=OFFICIAL_CHINESE_REUSE_POLICY,
)


def _compose_identities() -> tuple[_IdentityInput, ...]:
    iupac_records = load_iupac_elements()
    chinese_records = (*load_periodic_table_pro_names(), *load_official_chinese_names())
    chinese_by_number = {record.atomic_number: record for record in chinese_records}

    if len(chinese_records) != 118 or set(chinese_by_number) != set(range(1, 119)):
        raise IdentityCompositionError(
            "Chinese source composition must cover exactly 1 through 118"
        )
    if len({record.name_zh for record in chinese_records}) != 118:
        raise IdentityCompositionError("Chinese names must be complete and unique")

    composed: list[_IdentityInput] = []
    for iupac in iupac_records:
        chinese = chinese_by_number[iupac.atomic_number]
        if chinese.symbol != iupac.symbol:
            raise IdentityCompositionError(
                f"source symbol mismatch for atomic_number={iupac.atomic_number}"
            )
        composed.append(_IdentityInput(iupac=iupac, chinese=chinese))
    return tuple(composed)


def _upsert_source(session: Session, definition: _SourceDefinition) -> UUID:
    source = ElementDataBase.metadata.tables["element_source"]
    values = {
        "title": definition.title,
        "publisher": definition.publisher,
        "source_type": definition.source_type,
        "base_url": definition.base_url,
        "license_code": None,
        "reuse_policy": definition.reuse_policy,
    }
    source_id = session.scalar(
        pg_insert(source)
        .values(
            id=uuid4(),
            source_key=definition.source_key,
            **values,
        )
        .on_conflict_do_update(
            index_elements=[source.c.source_key],
            set_=values,
        )
        .returning(source.c.id)
    )
    if source_id is None:  # pragma: no cover - PostgreSQL RETURNING invariant
        raise RuntimeError("identity source upsert returned no id")
    return source_id


def _upsert_source_record(
    session: Session,
    source_id: UUID,
    record: _IdentitySourceRecord,
) -> tuple[UUID, bool]:
    source_record = ElementDataBase.metadata.tables["element_source_record"]
    inserted_id = session.scalar(
        pg_insert(source_record)
        .values(
            id=uuid4(),
            source_id=source_id,
            source_version=record.source_version,
            record_key=str(record.atomic_number),
            source_url=record.source_url,
            retrieved_at=record.retrieved_at,
            content_sha256=record.content_sha256,
            raw_payload=record.raw_payload,
        )
        .on_conflict_do_nothing(constraint="uq_element_source_record_identity")
        .returning(source_record.c.id)
    )
    if inserted_id is not None:
        return inserted_id, True
    existing_id = session.scalar(
        select(source_record.c.id).where(
            source_record.c.source_id == source_id,
            source_record.c.source_version == record.source_version,
            source_record.c.record_key == str(record.atomic_number),
            source_record.c.content_sha256 == record.content_sha256,
        )
    )
    if existing_id is None:  # pragma: no cover - conflict target invariant
        raise RuntimeError("identity source-record conflict returned no row")
    return existing_id, False


def _upsert_claim(
    session: Session,
    *,
    element_id: UUID,
    source_record_id: UUID,
    field_name: str,
    raw_value: str,
    transform_version: str,
    normalized_text: str | None = None,
    normalized_integer: int | None = None,
) -> tuple[UUID, bool]:
    claim = ElementDataBase.metadata.tables["element_claim"]
    values = {
        "element_id": element_id,
        "source_record_id": source_record_id,
        "field_name": field_name,
        "raw_value": raw_value,
        "normalized_text": normalized_text,
        "normalized_integer": normalized_integer,
        "verification_status": "verified",
        "transform_version": transform_version,
    }
    inserted_id = session.scalar(
        pg_insert(claim)
        .values(
            id=uuid4(),
            **values,
        )
        .on_conflict_do_nothing(constraint="uq_element_claim_transformation")
        .returning(claim.c.id)
    )
    if inserted_id is not None:
        return inserted_id, True

    existing = (
        session.execute(
            select(claim).where(
                claim.c.source_record_id == source_record_id,
                claim.c.field_name == field_name,
                claim.c.transform_version == transform_version,
            )
        )
        .mappings()
        .one_or_none()
    )
    if existing is None:  # pragma: no cover - conflict target invariant
        raise RuntimeError("identity claim conflict returned no row")
    expected = {
        "element_id": element_id,
        "raw_value": raw_value,
        "normalized_text": normalized_text,
        "normalized_integer": normalized_integer,
    }
    if any(existing[key] != value for key, value in expected.items()):
        raise IdentityCompositionError(
            f"existing {field_name} claim differs without a transform-version change"
        )
    return existing["id"], False


def _upsert_element(session: Session, identity: _IdentityInput) -> tuple[Element, bool]:
    element_table = ElementDataBase.metadata.tables["element"]
    candidate = Element(
        id=ElementId(uuid4()),
        atomic_number=AtomicNumber(identity.iupac.atomic_number),
        symbol=ElementSymbol(identity.iupac.symbol),
        name_zh=identity.chinese.name_zh,
        name_en=identity.iupac.name_en,
    )
    inserted_id = session.scalar(
        pg_insert(element_table)
        .values(
            id=candidate.id.value,
            atomic_number=candidate.atomic_number.value,
            symbol=candidate.symbol.value,
            name_zh=candidate.name_zh,
            name_en=candidate.name_en,
        )
        .on_conflict_do_nothing(index_elements=[element_table.c.atomic_number])
        .returning(element_table.c.id)
    )
    if inserted_id is not None:
        return candidate, True

    existing = (
        session.execute(
            select(element_table).where(
                element_table.c.atomic_number == candidate.atomic_number.value
            )
        )
        .mappings()
        .one_or_none()
    )
    if existing is None:  # pragma: no cover - conflict target invariant
        raise RuntimeError("identity element conflict returned no row")
    canonical = Element(
        id=ElementId(existing["id"]),
        atomic_number=AtomicNumber(existing["atomic_number"]),
        symbol=ElementSymbol(existing["symbol"]),
        name_zh=existing["name_zh"],
        name_en=existing["name_en"],
    )
    if (
        canonical.symbol != candidate.symbol
        or canonical.name_zh != candidate.name_zh
        or canonical.name_en != candidate.name_en
    ):
        raise IdentityCompositionError(
            f"canonical identity conflict for atomic_number={candidate.atomic_number.value}"
        )
    return canonical, False


def _publish_claim(
    session: Session,
    *,
    element_id: UUID,
    field_name: str,
    claim_id: UUID,
    source_key: str,
    selected_at: datetime,
) -> bool:
    published = ElementDataBase.metadata.tables["element_published_value"]
    current_claim_id = session.scalar(
        select(published.c.claim_id).where(
            published.c.element_id == element_id,
            published.c.field_name == field_name,
        )
    )
    if current_claim_id == claim_id:
        return False

    is_periodic_table_pro = source_key == PERIODIC_TABLE_PRO_SOURCE_KEY
    selection_method = "manual" if is_periodic_table_pro else "authority_policy"
    reason = (
        "Periodic Table PRO factual Chinese seed selected for bootstrap; not authoritative"
        if is_periodic_table_pro
        else f"{source_key} selected for its frozen authoritative identity field"
    )
    values = {
        "claim_id": claim_id,
        "selection_method": selection_method,
        "policy_version": IDENTITY_POLICY_VERSION,
        "selected_by": f"policy:{IDENTITY_POLICY_VERSION}",
        "selection_reason": reason,
        "selected_at": selected_at,
    }
    session.execute(
        pg_insert(published)
        .values(
            element_id=element_id,
            field_name=field_name,
            **values,
        )
        .on_conflict_do_update(
            index_elements=[published.c.element_id, published.c.field_name],
            set_=values,
        )
    )
    return True


def bootstrap_element_identities(session: Session) -> IdentityBootstrapResult:
    """Persist the approved 118-element identity composition in the caller's transaction."""

    identities = _compose_identities()
    source_ids = {
        IUPAC_SOURCE_KEY: _upsert_source(session, _IUPAC_SOURCE),
        PERIODIC_TABLE_PRO_SOURCE_KEY: _upsert_source(session, _PERIODIC_TABLE_PRO_SOURCE),
        OFFICIAL_CHINESE_SOURCE_KEY: _upsert_source(session, _OFFICIAL_CHINESE_SOURCE),
    }
    element_ids: list[ElementId] = []
    elements_created = 0
    source_records_created = 0
    claims_created = 0
    publications_changed = 0

    for identity in identities:
        element, element_created = _upsert_element(session, identity)
        elements_created += int(element_created)
        element_ids.append(element.id)

        iupac_record_id, iupac_record_created = _upsert_source_record(
            session,
            source_ids[IUPAC_SOURCE_KEY],
            identity.iupac,
        )
        chinese_record_id, chinese_record_created = _upsert_source_record(
            session,
            source_ids[identity.chinese.source_key],
            identity.chinese,
        )
        source_records_created += int(iupac_record_created) + int(chinese_record_created)
        iupac_claims = (
            (
                "atomic_number",
                str(identity.iupac.atomic_number),
                None,
                identity.iupac.atomic_number,
            ),
            ("symbol", identity.iupac.symbol, identity.iupac.symbol, None),
            ("name_en", identity.iupac.name_en, identity.iupac.name_en, None),
        )
        for field_name, raw_value, normalized_text, normalized_integer in iupac_claims:
            claim_id, claim_created = _upsert_claim(
                session,
                element_id=element.id.value,
                source_record_id=iupac_record_id,
                field_name=field_name,
                raw_value=raw_value,
                normalized_text=normalized_text,
                normalized_integer=normalized_integer,
                transform_version=IUPAC_TRANSFORM_VERSION,
            )
            claims_created += int(claim_created)
            publications_changed += int(
                _publish_claim(
                    session,
                    element_id=element.id.value,
                    field_name=field_name,
                    claim_id=claim_id,
                    source_key=IUPAC_SOURCE_KEY,
                    selected_at=identity.iupac.retrieved_at,
                )
            )

        chinese_transform_version = (
            PERIODIC_TABLE_PRO_TRANSFORM_VERSION
            if identity.chinese.source_key == PERIODIC_TABLE_PRO_SOURCE_KEY
            else OFFICIAL_CHINESE_TRANSFORM_VERSION
        )
        chinese_claim_id, chinese_claim_created = _upsert_claim(
            session,
            element_id=element.id.value,
            source_record_id=chinese_record_id,
            field_name="name_zh",
            raw_value=identity.chinese.name_zh,
            normalized_text=identity.chinese.name_zh,
            transform_version=chinese_transform_version,
        )
        claims_created += int(chinese_claim_created)
        publications_changed += int(
            _publish_claim(
                session,
                element_id=element.id.value,
                field_name="name_zh",
                claim_id=chinese_claim_id,
                source_key=identity.chinese.source_key,
                selected_at=identity.chinese.retrieved_at,
            )
        )

    return IdentityBootstrapResult(
        element_ids=tuple(element_ids),
        elements_created=elements_created,
        source_records_created=source_records_created,
        claims_created=claims_created,
        publications_changed=publications_changed,
    )
