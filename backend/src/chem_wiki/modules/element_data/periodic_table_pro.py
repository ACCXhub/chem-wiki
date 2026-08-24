"""Loader boundary for the factual Periodic Table PRO Chinese-name seed."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from chem_wiki.modules.chemistry_core import AtomicNumber, ElementSymbol

PERIODIC_TABLE_PRO_SOURCE_KEY = "periodic-table-pro-zhcn"
PERIODIC_TABLE_PRO_SOURCE_TITLE = "Periodic Table PRO Chinese Names"
PERIODIC_TABLE_PRO_PUBLISHER = "baotlake/periodic-table-pro contributors"
PERIODIC_TABLE_PRO_SOURCE_TYPE = "open_source"
PERIODIC_TABLE_PRO_REUSE_POLICY = "review_required"
PERIODIC_TABLE_PRO_TRANSFORM_VERSION = "periodic-table-pro-zhcn-v1"
_ARTIFACT = Path(__file__).with_name("seeds") / "periodic-table-pro-4b0446c.json"


class PeriodicTableProSeedError(ValueError):
    """Raised when the factual Chinese-name projection is malformed."""


@dataclass(frozen=True, slots=True)
class PeriodicTableProNameRecord:
    atomic_number: int
    symbol: str
    name_zh: str
    source_key: str
    source_version: str
    source_url: str
    citation_url: str
    retrieved_at: datetime
    content_sha256: str
    raw_value: str
    raw_payload: dict[str, object]


def load_periodic_table_pro_names(
    path: Path = _ARTIFACT,
) -> tuple[PeriodicTableProNameRecord, ...]:
    """Load only the 116 non-empty factual Chinese names from the pinned source."""

    try:
        artifact: Any = json.loads(path.read_text(encoding="utf-8"))
        metadata = artifact["metadata"]
        rows = artifact["records"]
        retrieved_at = datetime.fromisoformat(metadata["retrieved_at"])
        source_version = str(metadata["source_version"])
        source_url = str(metadata["source_url"])
        citation_url = str(metadata["citation_url"])
        source_hash = str(metadata["source_content_sha256"])
    except (OSError, json.JSONDecodeError, KeyError, AttributeError, TypeError, ValueError) as exc:
        raise PeriodicTableProSeedError("Periodic Table PRO seed artifact is invalid") from exc
    if len(source_hash) != 64 or any(char not in "0123456789abcdef" for char in source_hash):
        raise PeriodicTableProSeedError("Periodic Table PRO source hash is invalid")

    records: list[PeriodicTableProNameRecord] = []
    try:
        for number, raw_symbol, raw_name in rows:
            atomic_number = AtomicNumber(int(number)).value
            symbol = ElementSymbol(str(raw_symbol).strip()).value
            name_zh = str(raw_name).strip()
            if not name_zh:
                raise ValueError("blank Chinese name")
            raw_payload = {
                "atomic_number": atomic_number,
                "symbol": symbol,
                "name_zh": name_zh,
            }
            raw_value = json.dumps(raw_payload, ensure_ascii=False, separators=(",", ":"))
            records.append(
                PeriodicTableProNameRecord(
                    atomic_number=atomic_number,
                    symbol=symbol,
                    name_zh=name_zh,
                    source_key=PERIODIC_TABLE_PRO_SOURCE_KEY,
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
        raise PeriodicTableProSeedError("Periodic Table PRO seed record is invalid") from exc

    if [record.atomic_number for record in records] != list(range(1, 117)):
        raise PeriodicTableProSeedError("Periodic Table PRO seed must cover exactly 1 through 116")
    if len({record.name_zh for record in records}) != 116:
        raise PeriodicTableProSeedError("Periodic Table PRO Chinese names must be unique")
    return tuple(records)
