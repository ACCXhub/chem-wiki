"""Loader boundary for official Chinese names of elements 117 and 118."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from chem_wiki.modules.chemistry_core import AtomicNumber, ElementSymbol

OFFICIAL_CHINESE_SOURCE_KEY = "cnctst-official-element-names-2017"
OFFICIAL_CHINESE_SOURCE_TITLE = "Official Chinese Names for Elements 117 and 118"
OFFICIAL_CHINESE_PUBLISHER = "China National Committee for Terms in Sciences and Technologies"
OFFICIAL_CHINESE_SOURCE_TYPE = "standard"
OFFICIAL_CHINESE_REUSE_POLICY = "allowed"
OFFICIAL_CHINESE_TRANSFORM_VERSION = "cnctst-elements-117-118-v1"
_ARTIFACT = Path(__file__).with_name("seeds") / "official-chinese-elements-117-118.json"


class OfficialChineseNameSeedError(ValueError):
    """Raised when the official two-name factual projection is malformed."""


@dataclass(frozen=True, slots=True)
class OfficialChineseNameRecord:
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


def load_official_chinese_names(
    path: Path = _ARTIFACT,
) -> tuple[OfficialChineseNameRecord, ...]:
    """Load the approved factual supplement without retaining its source artwork."""

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
        raise OfficialChineseNameSeedError(
            "official Chinese-name seed artifact is invalid"
        ) from exc
    if len(source_hash) != 64 or any(char not in "0123456789abcdef" for char in source_hash):
        raise OfficialChineseNameSeedError("official Chinese-name source hash is invalid")

    records: list[OfficialChineseNameRecord] = []
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
                OfficialChineseNameRecord(
                    atomic_number=atomic_number,
                    symbol=symbol,
                    name_zh=name_zh,
                    source_key=OFFICIAL_CHINESE_SOURCE_KEY,
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
        raise OfficialChineseNameSeedError("official Chinese-name seed record is invalid") from exc

    if [(record.atomic_number, record.name_zh) for record in records] != [
        (117, "鿬"),
        (118, "鿫"),
    ]:
        raise OfficialChineseNameSeedError("official supplement must contain only 117 and 118")
    return tuple(records)
