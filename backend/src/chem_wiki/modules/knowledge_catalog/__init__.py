"""Application-owned consolidated knowledge catalog boundary."""

from .api import CatalogReader, get_catalog_reader
from .importer import KnowledgeCatalogImportResult, import_consolidated_release
from .persistence import (
    CatalogKnowledgeRecordRow,
    CatalogReactionParticipantRow,
    CatalogReactionRow,
    CatalogReleaseArtifactRow,
    CatalogReleaseRow,
    CatalogSourceCrosswalkRow,
    CatalogSpeciesRow,
    CatalogStructureLinkRow,
    CatalogStructureRecordRow,
    CatalogTeachingProjectionRow,
    KnowledgeCatalogBase,
)
from .postgres import PostgresCatalogReader
from .read_model import (
    CatalogKnowledgeResult,
    CatalogReactionParticipantResult,
    CatalogReactionResult,
    CatalogSpeciesResult,
    CatalogStructureEntry,
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
    "CatalogKnowledgeRecordRow",
    "CatalogKnowledgeResult",
    "CatalogReactionParticipantResult",
    "CatalogReactionParticipantRow",
    "CatalogReactionResult",
    "CatalogReactionRow",
    "CatalogReader",
    "CatalogReleaseArtifactRow",
    "CatalogReleaseRow",
    "CatalogSourceCrosswalkRow",
    "CatalogSpeciesResult",
    "CatalogSpeciesRow",
    "CatalogStructureEntry",
    "CatalogStructureLinkRow",
    "CatalogStructureRecordRow",
    "CatalogTeachingProjectionRow",
    "KnowledgeCatalogBase",
    "KnowledgeCatalogImportResult",
    "PinnedRelease",
    "PostgresCatalogReader",
    "ReleaseSourceIdentity",
    "ReleaseValidationError",
    "VerifiedArtifact",
    "VerifiedRelease",
    "get_catalog_reader",
    "import_consolidated_release",
    "read_git_source_identity",
    "verify_release",
]
