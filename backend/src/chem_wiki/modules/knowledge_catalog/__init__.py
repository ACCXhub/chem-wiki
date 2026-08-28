"""Application-owned consolidated knowledge catalog boundary."""

from .importer import KnowledgeCatalogImportResult, import_consolidated_release
from .persistence import (
    CatalogReactionParticipantRow,
    CatalogReactionRow,
    CatalogReleaseArtifactRow,
    CatalogReleaseRow,
    CatalogSourceCrosswalkRow,
    CatalogSpeciesRow,
    CatalogStructureLinkRow,
    CatalogTeachingProjectionRow,
    KnowledgeCatalogBase,
)
from .postgres import PostgresCatalogReader
from .api import CatalogReader, get_catalog_reader
from .read_model import (
    CatalogReactionParticipantResult,
    CatalogReactionResult,
    CatalogSpeciesResult,
)
from .release import (
    PINNED_RELEASE,
    PinnedRelease,
    ReleaseSourceIdentity,
    ReleaseValidationError,
    VerifiedArtifact,
    VerifiedRelease,
    read_git_source_identity,
    verify_release,
)

__all__ = [
    "PINNED_RELEASE",
    "CatalogReactionParticipantResult",
    "CatalogReactionParticipantRow",
    "CatalogReactionResult",
    "CatalogReactionRow",
    "CatalogReleaseArtifactRow",
    "CatalogReleaseRow",
    "CatalogSourceCrosswalkRow",
    "CatalogSpeciesResult",
    "CatalogSpeciesRow",
    "CatalogReader",
    "CatalogStructureLinkRow",
    "CatalogTeachingProjectionRow",
    "KnowledgeCatalogBase",
    "KnowledgeCatalogImportResult",
    "PinnedRelease",
    "PostgresCatalogReader",
    "ReleaseSourceIdentity",
    "ReleaseValidationError",
    "VerifiedArtifact",
    "VerifiedRelease",
    "import_consolidated_release",
    "get_catalog_reader",
    "read_git_source_identity",
    "verify_release",
]
