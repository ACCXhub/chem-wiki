"""PubChem PUG REST adapter for the periodic-table source schema."""

import json
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from chem_wiki.modules.chemistry_core import AtomicNumber, ElementSymbol

PUBCHEM_PERIODIC_TABLE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON"
PUBCHEM_SOURCE_VERSION = "pug-periodictable-json-v1"
PUBCHEM_CITATION_URL = "https://pubchem.ncbi.nlm.nih.gov/docs/citation-guidelines"
PUBCHEM_PUBLISHABLE_FIELDS = frozenset(
    {"electronegativity", "first_ionization_energy", "atomic_radius"}
)
PUBCHEM_TRANSFORM_VERSION = "pubchem-periodictable-v1"

_REQUIRED_COLUMNS = frozenset(
    {
        "AtomicNumber",
        "Symbol",
        "Name",
        "Electronegativity",
        "AtomicRadius",
        "IonizationEnergy",
    }
)


class PubChemPayloadError(ValueError):
    """Raised when the official response does not match its table envelope."""


class PubChemRequestError(RuntimeError):
    """Raised when PUG REST cannot provide a usable response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ElementNormalizationError(ValueError):
    """Raised when PubChem values cannot form valid M02 claims."""


@dataclass(frozen=True, slots=True)
class PubChemRawRecord:
    record_key: str
    source_version: str
    source_url: str
    retrieved_at: datetime
    content_sha256: str
    raw_payload: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class NormalizedClaim:
    field_name: str
    raw_value: str
    normalized_text: str | None = None
    normalized_integer: int | None = None
    normalized_numeric: Decimal | None = None
    canonical_unit: str | None = None
    qualifier: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedElementRecord:
    raw_record: PubChemRawRecord
    atomic_number: int
    symbol: str
    name_en: str
    claims: tuple[NormalizedClaim, ...]
    publishable_fields: frozenset[str]


FetchJson = Callable[[str, float], Mapping[str, Any]]
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _fetch_json(url: str, timeout: float) -> Mapping[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "chem-wiki-m02/0.1 (PubChem PUG REST client)",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise PubChemRequestError(
            f"PubChem request failed with HTTP {exc.code}",
            status_code=exc.code,
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PubChemRequestError(f"PubChem request failed: {exc}") from exc

    if not isinstance(payload, Mapping):
        raise PubChemPayloadError("PubChem response must be a JSON object")
    return payload


def _decimal_claim(
    raw_payload: dict[str, str],
    source_field: str,
    field_name: str,
    *,
    canonical_unit: str | None = None,
    qualifier: str | None = None,
) -> NormalizedClaim | None:
    raw_value = raw_payload[source_field].strip()
    if not raw_value:
        return None
    try:
        normalized_value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ElementNormalizationError(
            f"PubChem {source_field} is not a decimal: {raw_value!r}"
        ) from exc
    if not normalized_value.is_finite() or normalized_value <= 0:
        raise ElementNormalizationError(f"PubChem {source_field} must be a positive finite value")
    return NormalizedClaim(
        field_name=field_name,
        raw_value=raw_value,
        normalized_numeric=normalized_value,
        canonical_unit=canonical_unit,
        qualifier=qualifier,
    )


def _normalize_record(record: PubChemRawRecord) -> NormalizedElementRecord:
    raw_payload = dict(record.raw_payload)
    try:
        atomic_number = int(raw_payload["AtomicNumber"])
        if atomic_number > 118:
            raise ValueError("atomic number exceeds the canonical range")
        AtomicNumber(atomic_number)
        symbol = ElementSymbol(raw_payload["Symbol"].strip()).value
        name_en = raw_payload["Name"].strip().lower()
        if not name_en:
            raise ValueError("English name is blank")
    except (KeyError, TypeError, ValueError) as exc:
        raise ElementNormalizationError("invalid PubChem element identity") from exc

    claims: list[NormalizedClaim] = [
        NormalizedClaim(
            field_name="atomic_number",
            raw_value=raw_payload["AtomicNumber"],
            normalized_integer=atomic_number,
        ),
        NormalizedClaim(
            field_name="symbol",
            raw_value=raw_payload["Symbol"],
            normalized_text=symbol,
        ),
        NormalizedClaim(
            field_name="name_en",
            raw_value=raw_payload["Name"],
            normalized_text=name_en,
        ),
    ]
    optional_claims = (
        _decimal_claim(
            raw_payload,
            "Electronegativity",
            "electronegativity",
            qualifier="Pauling",
        ),
        _decimal_claim(
            raw_payload,
            "AtomicRadius",
            "atomic_radius",
            canonical_unit="pm",
            qualifier="atomic",
        ),
        _decimal_claim(
            raw_payload,
            "IonizationEnergy",
            "first_ionization_energy",
            canonical_unit="eV",
        ),
    )
    claims.extend(claim for claim in optional_claims if claim is not None)
    return NormalizedElementRecord(
        raw_record=record,
        atomic_number=atomic_number,
        symbol=symbol,
        name_en=name_en,
        claims=tuple(claims),
        publishable_fields=PUBCHEM_PUBLISHABLE_FIELDS,
    )


class PubChemAdapter:
    """Translate the PubChem table envelope into per-element raw records."""

    def __init__(
        self,
        *,
        fetch_json: FetchJson = _fetch_json,
        clock: Clock = _utc_now,
        timeout: float = 30.0,
    ) -> None:
        self._fetch_json = fetch_json
        self._clock = clock
        self._timeout = timeout

    def fetch_elements(self, atomic_numbers: Collection[int]) -> tuple[PubChemRawRecord, ...]:
        requested = frozenset(atomic_numbers)
        if not requested or any(number < 1 or number > 118 for number in requested):
            raise ValueError("atomic_numbers must contain values from 1 through 118")

        payload = self._fetch_json(PUBCHEM_PERIODIC_TABLE_URL, self._timeout)
        retrieved_at = self._clock()
        records = self._parse_records(payload, retrieved_at)
        selected = tuple(
            record for record in records if int(record.raw_payload["AtomicNumber"]) in requested
        )
        found = {int(record.raw_payload["AtomicNumber"]) for record in selected}
        missing = sorted(requested - found)
        if missing:
            raise PubChemPayloadError(f"PubChem response omitted atomic numbers: {missing}")
        return selected

    @staticmethod
    def normalize(record: PubChemRawRecord) -> NormalizedElementRecord:
        """Normalize one source record while keeping PubChem columns inside the adapter."""

        return _normalize_record(record)

    @staticmethod
    def _parse_records(
        payload: Mapping[str, Any],
        retrieved_at: datetime,
    ) -> tuple[PubChemRawRecord, ...]:
        try:
            table = payload["Table"]
            columns = table["Columns"]["Column"]
            rows = table["Row"]
        except (KeyError, TypeError) as exc:
            raise PubChemPayloadError("PubChem response is missing its table envelope") from exc

        if not isinstance(columns, list) or not all(isinstance(item, str) for item in columns):
            raise PubChemPayloadError("PubChem columns must be a list of names")
        missing_columns = sorted(_REQUIRED_COLUMNS - set(columns))
        if missing_columns:
            raise PubChemPayloadError(f"PubChem response omitted columns: {missing_columns}")
        if not isinstance(rows, list):
            raise PubChemPayloadError("PubChem rows must be a list")

        records: list[PubChemRawRecord] = []
        for row in rows:
            cells = row.get("Cell") if isinstance(row, Mapping) else None
            if not isinstance(cells, list) or len(cells) != len(columns):
                raise PubChemPayloadError("PubChem row column count does not match schema")
            if not all(isinstance(cell, (str, int, float)) or cell is None for cell in cells):
                raise PubChemPayloadError("PubChem row contains an unsupported cell value")
            raw_payload = {
                column: "" if cell is None else str(cell)
                for column, cell in zip(columns, cells, strict=True)
            }
            record_key = raw_payload["AtomicNumber"]
            if not record_key:
                raise PubChemPayloadError("PubChem row has no AtomicNumber")
            canonical_json = json.dumps(
                raw_payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
            records.append(
                PubChemRawRecord(
                    record_key=record_key,
                    source_version=PUBCHEM_SOURCE_VERSION,
                    source_url=PUBCHEM_PERIODIC_TABLE_URL,
                    retrieved_at=retrieved_at,
                    content_sha256=sha256(canonical_json).hexdigest(),
                    raw_payload=raw_payload,
                )
            )
        return tuple(records)
