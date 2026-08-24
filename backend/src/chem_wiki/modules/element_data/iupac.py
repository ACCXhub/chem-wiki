"""Loader boundary for the versioned IUPAC periodic-table identity seed."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from chem_wiki.modules.chemistry_core import AtomicNumber, ElementSymbol

IUPAC_SOURCE_KEY = "iupac-periodic-table-2022"
IUPAC_SOURCE_TITLE = "IUPAC Periodic Table of the Elements"
IUPAC_PUBLISHER = "International Union of Pure and Applied Chemistry"
IUPAC_SOURCE_TYPE = "standard"
IUPAC_REUSE_POLICY = "allowed"
IUPAC_TRANSFORM_VERSION = "iupac-identity-2022-v1"
_ARTIFACT = Path(__file__).with_name("seeds") / "iupac-periodic-table-2022-05-04.json"


class IupacSeedError(ValueError):
    """Raised when the audited IUPAC seed is incomplete or malformed."""


@dataclass(frozen=True, slots=True)
class IupacElementRecord:
    atomic_number: int
    symbol: str
    name_en: str
    source_key: str
    source_version: str
    source_url: str
    citation_url: str
    retrieved_at: datetime
    content_sha256: str
    raw_value: str
    raw_payload: dict[str, object]


def _load_artifact(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IupacSeedError("IUPAC seed artifact is unreadable") from exc
    if not isinstance(value, dict):
        raise IupacSeedError("IUPAC seed artifact must be an object")
    return value


def load_iupac_elements(path: Path = _ARTIFACT) -> tuple[IupacElementRecord, ...]:
    """Load and validate the audited 2022 IUPAC identity projection."""

    artifact = _load_artifact(path)
    try:
        metadata = artifact["metadata"]
        rows = artifact["records"]
        retrieved_at = datetime.fromisoformat(metadata["retrieved_at"])
        source_version = str(metadata["source_version"])
        source_url = str(metadata["source_url"])
        citation_url = str(metadata["citation_url"])
        source_hash = str(metadata["source_content_sha256"])
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise IupacSeedError("IUPAC seed metadata is invalid") from exc
    if len(source_hash) != 64 or any(char not in "0123456789abcdef" for char in source_hash):
        raise IupacSeedError("IUPAC source hash is invalid")

    records: list[IupacElementRecord] = []
    try:
        for number, raw_symbol, raw_name in rows:
            atomic_number = AtomicNumber(int(number)).value
            symbol = ElementSymbol(str(raw_symbol).strip()).value
            name_en = str(raw_name).strip().lower()
            if not name_en:
                raise ValueError("blank English name")
            raw_payload = {
                "atomic_number": atomic_number,
                "symbol": symbol,
                "name_en": name_en,
            }
            raw_value = json.dumps(raw_payload, ensure_ascii=False, separators=(",", ":"))
            records.append(
                IupacElementRecord(
                    atomic_number=atomic_number,
                    symbol=symbol,
                    name_en=name_en,
                    source_key=IUPAC_SOURCE_KEY,
                    source_version=source_version,
                    source_url=source_url,
                    citation_url=citation_url,
                    retrieved_at=retrieved_at,
                    content_sha256=sha256(raw_value.encode()).hexdigest(),
                    raw_value=raw_value,
                    raw_payload=raw_payload,
                )
            )
    except (TypeError, ValueError) as exc:
        raise IupacSeedError("IUPAC seed record is invalid") from exc

    if [record.atomic_number for record in records] != list(range(1, 119)):
        raise IupacSeedError("IUPAC seed must cover atomic numbers 1 through 118")
    if len({record.symbol for record in records}) != 118:
        raise IupacSeedError("IUPAC symbols must be unique")
    if len({record.name_en for record in records}) != 118:
        raise IupacSeedError("IUPAC English names must be unique")
    return tuple(records)
