from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProvenanceRef:
    source_id: str
    source_url: str | None = None
    citation: str | None = None
    retrieved_at: datetime | None = None
    source_version: str | None = None

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        if not source_id:
            raise ValueError("source_id must not be blank")
        object.__setattr__(self, "source_id", source_id)
