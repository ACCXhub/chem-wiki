"""NIST ASD adapter for neutral-atom first ionization energies."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from chem_wiki.modules.chemistry_core import AtomicNumber, ElementSymbol

NIST_ASD_ENDPOINT = "https://physics.nist.gov/cgi-bin/ASD/ie.pl"
NIST_ASD_BASE_URL = "https://physics.nist.gov/PhysRefData/ASD/ionEnergy.html"
NIST_ASD_SOURCE_VERSION = "nist-asd-5.12"
NIST_ASD_TRANSFORM_VERSION = "nist-asd-neutral-ie-5.12-v1"
NIST_ASD_CITATION = (
    "Kramida, A., Ralchenko, Yu., Reader, J., and NIST ASD Team (2024). "
    "NIST Atomic Spectra Database (ver. 5.12), [Online]. "
    "Available: https://physics.nist.gov/asd"
)

_REQUESTED_COLUMNS = (
    "At. num",
    "Sp. Name",
    "Ion Charge",
    "El. Name",
    "Prefix",
    "Ionization Energy (eV)",
    "Suffix",
    "Uncertainty (eV)",
    "References",
)

FetchText = Callable[[str, float], str]
Clock = Callable[[], datetime]


class NistAsdPayloadError(ValueError):
    """Raised when NIST ASD does not return the frozen neutral-atom projection."""


class NistAsdRequestError(RuntimeError):
    """Raised when the official NIST ASD request cannot be completed."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class NistAsdRawRecord:
    atomic_number: int
    symbol: str
    record_key: str
    source_version: str
    source_url: str
    retrieved_at: datetime
    content_sha256: str
    raw_payload: Mapping[str, str]
    raw_value: str
    value_ev: Decimal
    uncertainty_ev: Decimal | None
    qualifier: str | None


@dataclass(frozen=True, slots=True)
class NistAsdClaim:
    field_name: str
    raw_value: str
    normalized_numeric: Decimal
    canonical_unit: str
    uncertainty: Decimal | None
    qualifier: str | None


def _default_fetch_text(url: str, timeout: float) -> str:
    request = Request(
        url,
        headers={"User-Agent": "chem-wiki-m02/0.1 (NIST ASD calibration client)"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8-sig")
    except HTTPError as exc:
        raise NistAsdRequestError(
            f"NIST ASD request failed with HTTP {exc.code}",
            status_code=exc.code,
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise NistAsdRequestError(f"NIST ASD request failed: {exc}") from exc


def _unwrap_cell(value: str | None) -> str:
    if value is None:
        return ""
    stripped = value.strip()
    if stripped.startswith('="') and stripped.endswith('"'):
        return stripped[2:-1]
    return stripped


def _parse_decimal(raw_value: str, *, field_name: str, allow_zero: bool) -> Decimal:
    try:
        value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise NistAsdPayloadError(f"NIST ASD {field_name} is not decimal: {raw_value!r}") from exc
    if not value.is_finite() or value < 0 or (not allow_zero and value == 0):
        raise NistAsdPayloadError(f"NIST ASD {field_name} is outside its valid range")
    return value


def _content_hash(payload: Mapping[str, str]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class NistAsdAdapter:
    """Fetch and normalize only neutral-atom first ionization energies from NIST ASD."""

    def __init__(
        self,
        *,
        fetch_text: FetchText = _default_fetch_text,
        clock: Clock = lambda: datetime.now(UTC),
        timeout: float = 30.0,
    ) -> None:
        self._fetch_text = fetch_text
        self._clock = clock
        self._timeout = timeout

    def fetch_neutral_atoms(self, symbols: Collection[str]) -> tuple[NistAsdRawRecord, ...]:
        requested = {ElementSymbol(symbol).value for symbol in symbols}
        if not requested:
            return ()

        spectra = ";".join(f"{symbol} I" for symbol in sorted(requested, key=str.casefold))
        query = urlencode(
            {
                "spectra": spectra,
                "units": "1",
                "format": "2",
                "order": "0",
                "at_num_out": "on",
                "sp_name_out": "on",
                "ion_charge_out": "on",
                "el_name_out": "on",
                "e_out": "0",
                "unc_out": "on",
                "biblio": "on",
            }
        )
        source_url = f"{NIST_ASD_ENDPOINT}?{query}"
        raw_csv = self._fetch_text(source_url, self._timeout)
        retrieved_at = self._clock()
        records = self._parse_response(raw_csv, source_url=source_url, retrieved_at=retrieved_at)

        found = {record.symbol for record in records}
        if found != requested:
            raise NistAsdPayloadError(
                f"NIST ASD neutral-atom response mismatch; missing={sorted(requested - found)}, "
                f"unexpected={sorted(found - requested)}"
            )
        return tuple(sorted(records, key=lambda record: record.atomic_number))

    @staticmethod
    def normalize(record: NistAsdRawRecord) -> NistAsdClaim:
        return NistAsdClaim(
            field_name="first_ionization_energy",
            raw_value=record.raw_value,
            normalized_numeric=record.value_ev,
            canonical_unit="eV",
            uncertainty=record.uncertainty_ev,
            qualifier=record.qualifier,
        )

    @staticmethod
    def _parse_response(
        raw_csv: str,
        *,
        source_url: str,
        retrieved_at: datetime,
    ) -> list[NistAsdRawRecord]:
        reader = csv.DictReader(io.StringIO(raw_csv))
        if reader.fieldnames is None or not set(_REQUESTED_COLUMNS).issubset(reader.fieldnames):
            raise NistAsdPayloadError(
                "NIST ASD response omitted required ionization-energy columns"
            )

        records: list[NistAsdRawRecord] = []
        seen_atomic_numbers: set[int] = set()
        for source_row in reader:
            row = {column: _unwrap_cell(source_row.get(column)) for column in _REQUESTED_COLUMNS}
            try:
                atomic_number = AtomicNumber(int(row["At. num"])).value
                spectrum = row["Sp. Name"]
                if not spectrum.endswith(" I") or row["Ion Charge"] != "0":
                    raise NistAsdPayloadError("NIST ASD row is not a neutral atom")
                symbol = ElementSymbol(spectrum.removesuffix(" I")).value
            except (TypeError, ValueError) as exc:
                if isinstance(exc, NistAsdPayloadError):
                    raise
                raise NistAsdPayloadError("NIST ASD neutral-atom identity is invalid") from exc

            if atomic_number in seen_atomic_numbers:
                raise NistAsdPayloadError(
                    f"NIST ASD response duplicated atomic_number={atomic_number}"
                )
            seen_atomic_numbers.add(atomic_number)

            raw_value = row["Ionization Energy (eV)"]
            value_ev = _parse_decimal(
                raw_value,
                field_name="ionization energy",
                allow_zero=False,
            )
            raw_uncertainty = row["Uncertainty (eV)"]
            uncertainty_ev = (
                _parse_decimal(raw_uncertainty, field_name="uncertainty", allow_zero=True)
                if raw_uncertainty
                else None
            )
            qualifier = f"{row['Prefix']}{row['Suffix']}" or None
            raw_payload = {**row, "ASD Citation": NIST_ASD_CITATION}
            records.append(
                NistAsdRawRecord(
                    atomic_number=atomic_number,
                    symbol=symbol,
                    record_key=spectrum,
                    source_version=NIST_ASD_SOURCE_VERSION,
                    source_url=source_url,
                    retrieved_at=retrieved_at,
                    content_sha256=_content_hash(raw_payload),
                    raw_payload=raw_payload,
                    raw_value=raw_value,
                    value_ev=value_ev,
                    uncertainty_ev=uncertainty_ev,
                    qualifier=qualifier,
                )
            )
        return records
