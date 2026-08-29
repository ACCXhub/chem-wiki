"""Typed access to the versioned element teaching relation index."""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

TeachingPriority = Literal["core", "common", "extended"]


@dataclass(frozen=True, slots=True)
class TeachingRelation:
    consolidated_id: str
    teaching_priority: TeachingPriority


@dataclass(frozen=True, slots=True)
class ElementTeachingRelations:
    atomic_number: int
    symbol: str
    species: tuple[TeachingRelation, ...]
    reactions: tuple[TeachingRelation, ...]


@lru_cache(maxsize=1)
def load_element_teaching_relations() -> dict[int, ElementTeachingRelations]:
    seed_root = Path(__file__).with_name("seeds")
    data_path = seed_root / "element-teaching-relations.jsonl"
    metadata = json.loads(
        (seed_root / "element-teaching-relations.meta.json").read_text(encoding="utf-8")
    )
    content = data_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != metadata["content_sha256"]:
        raise ValueError("element teaching relation snapshot SHA-256 is invalid")
    records: dict[int, ElementTeachingRelations] = {}
    for line in content.decode("utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        atomic_number = int(item["atomic_number"])
        records[atomic_number] = ElementTeachingRelations(
            atomic_number=atomic_number,
            symbol=str(item["symbol"]),
            species=tuple(
                TeachingRelation(
                    consolidated_id=str(value["species_id"]),
                    teaching_priority=value["teaching_priority"],
                )
                for value in item["related_species"]
            ),
            reactions=tuple(
                TeachingRelation(
                    consolidated_id=str(value["reaction_id"]),
                    teaching_priority=value["teaching_priority"],
                )
                for value in item["related_reactions"]
            ),
        )
    if len(records) != metadata["record_count"]:
        raise ValueError("element teaching relation snapshot count is invalid")
    return records
