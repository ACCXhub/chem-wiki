"""Deterministic import orchestration for the pinned consolidated release."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.orm import Session

from chem_wiki.modules.chemistry_core import (
    Condition,
    IonId,
    Phase,
    ProvenanceRef,
    Reaction,
    ReactionCode,
    ReactionId,
    ReactionParticipant,
    ReactionParticipantId,
    ReactionRole,
    ReactionStatus,
    StoichiometricCoefficient,
    SubstanceId,
)
from chem_wiki.modules.reaction_core import (
    EquationMode,
    PostgresReactionRepository,
    ReactionDocument,
    ReactionRow,
)

from .persistence import (
    CatalogKnowledgeRecordRow,
    CatalogReactionParticipantRow,
    CatalogReactionRow,
    CatalogReleaseArtifactRow,
    CatalogReleaseRow,
    CatalogSourceAttributionRow,
    CatalogSourceCrosswalkRow,
    CatalogSpeciesRow,
    CatalogStructureLinkRow,
    CatalogStructureRecordRow,
    CatalogTeachingProjectionRow,
)
from .release import PINNED_RELEASE, ReleaseSourceIdentity, VerifiedRelease, verify_release

SPECIES_NAMESPACE = uuid5(NAMESPACE_URL, "chem-wiki:knowledge-catalog:species:v1")
STRUCTURE_NAMESPACE = uuid5(NAMESPACE_URL, "chem-wiki:knowledge-catalog:structure:v1")
REACTION_NAMESPACE = uuid5(NAMESPACE_URL, "chem-wiki:knowledge-catalog:reaction:v1")
PARTICIPANT_NAMESPACE = uuid5(NAMESPACE_URL, "chem-wiki:knowledge-catalog:participant:v1")
KNOWLEDGE_NAMESPACE = uuid5(NAMESPACE_URL, "chem-wiki:knowledge-catalog:knowledge:v1")


@dataclass(frozen=True, slots=True)
class KnowledgeCatalogImportResult:
    species_imported: int
    teaching_projections_imported: int
    structure_links_imported: int
    catalog_reactions_imported: int
    m05_reactions_materialized: int
    catalog_only_reactions: int
    knowledge_records_imported: int
    structure_records_imported: int
    source_attributions_imported: int


def _load_jsonl(release: VerifiedRelease, name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        release.artifacts[name].path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{name}:{line_number} 不是有效 JSON") from error
        if not isinstance(payload, dict):
            raise TypeError(f"{name}:{line_number} 必须是 JSON object")
        records.append(payload)
    return records


def _stable_uuid(namespace: UUID, external_id: str) -> UUID:
    return uuid5(namespace, external_id)


def _store_release(session: Session, release: VerifiedRelease) -> None:
    row = session.get(CatalogReleaseRow, release.release)
    if row is None:
        session.add(
            CatalogReleaseRow(
                release=release.release,
                repository=PINNED_RELEASE.repository,
                commit=PINNED_RELEASE.commit,
                state=release.state,
                manifest_sha256=release.manifest_sha256,
                imported_at=datetime.now(UTC),
            )
        )
        session.flush()
    elif row.manifest_sha256 != release.manifest_sha256:
        raise ValueError("同一 consolidated release 的 manifest hash 不可改变")

    for artifact in release.artifacts.values():
        key = (release.release, artifact.name)
        if session.get(CatalogReleaseArtifactRow, key) is None:
            session.add(
                CatalogReleaseArtifactRow(
                    release=release.release,
                    artifact_name=artifact.name,
                    sha256=artifact.sha256,
                    records=artifact.records,
                )
            )


def _import_species(
    session: Session, records: list[dict[str, Any]]
) -> dict[str, CatalogSpeciesRow]:
    mappings: dict[str, CatalogSpeciesRow] = {}
    for record in records:
        consolidated_id = str(record["id"])
        row = session.get(CatalogSpeciesRow, consolidated_id)
        if row is None:
            row = CatalogSpeciesRow(
                consolidated_id=consolidated_id,
                application_id=_stable_uuid(SPECIES_NAMESPACE, consolidated_id),
                entity_kind=str(record["entity_kind"]),
                source_ids=list(record["source_ids"]),
                name_zh=str(record["name_zh"]),
                name_en=record.get("name_en"),
                formula=str(record["formula"]),
                charge=int(record["charge"]),
                composition=record.get("composition"),
                aliases=list(record["aliases"]),
                chemical_classifications=list(record["chemical_classifications"]),
                teaching_priority=str(record["teaching_priority"]),
                source_review_states=list(record["source_review_states"]),
                integration_status=str(record["integration_status"]),
                provenance_refs=list(record["provenance_refs"]),
                external_ids=list(record["external_ids"]),
                preferred_structure_id=record.get("preferred_structure_id"),
            )
            session.add(row)
        elif row.entity_kind != record["entity_kind"]:
            raise ValueError(f"consolidated species kind 不可改变：{consolidated_id}")
        mappings[consolidated_id] = row
    session.flush()
    return mappings


def _import_crosswalks(session: Session, records: list[dict[str, Any]]) -> None:
    for record in records:
        key = (str(record["source_package"]), str(record["source_id"]))
        if session.get(CatalogSourceCrosswalkRow, key) is None:
            session.add(
                CatalogSourceCrosswalkRow(
                    source_package=key[0],
                    source_id=key[1],
                    source_entity_type=str(record["source_entity_type"]),
                    consolidated_id=str(record["consolidated_id"]),
                    mapping_status=str(record["mapping_status"]),
                    resolution_method=str(record["resolution_method"]),
                    evidence_refs=list(record["evidence_refs"]),
                    notes=record.get("notes"),
                )
            )


def _import_source_attributions(session: Session, release: VerifiedRelease) -> int:
    registry_path = (
        release.source_root / "packages" / "inorganic" / "sources" / "source_registry.json"
    )
    if not registry_path.is_file():
        raise ValueError("pinned inorganic package 缺少 source registry")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise TypeError("pinned inorganic source registry 格式无效")
    imported = 0
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        name = source.get("name")
        if not isinstance(source_id, str) or not isinstance(name, str):
            continue
        source_ref = f"inorganic:{source_id}"
        if session.get(CatalogSourceAttributionRow, source_ref) is None:
            session.add(
                CatalogSourceAttributionRow(
                    source_ref=source_ref,
                    name=name,
                    url=source.get("url") if isinstance(source.get("url"), str) else None,
                )
            )
        imported += 1
    return imported


def _import_teaching_projections(session: Session, records: list[dict[str, Any]]) -> None:
    for record in records:
        species_id = str(record["species_id"])
        if session.get(CatalogTeachingProjectionRow, species_id) is not None:
            continue
        modes = record["equation_modes"]
        session.add(
            CatalogTeachingProjectionRow(
                species_id=species_id,
                primary_category=str(record["primary_category"]),
                tags=list(record["tags"]),
                search_tokens=list(record["search_tokens"]),
                default_priority=str(record["default_priority"]),
                default_palette_rank=int(record["default_palette_rank"]),
                molecular_suitability=str(modes["molecular"]),
                ionic_suitability=str(modes["ionic"]),
                net_ionic_suitability=str(modes["net_ionic"]),
            )
        )


def _import_structure_links(
    session: Session,
    records: list[dict[str, Any]],
    species: dict[str, CatalogSpeciesRow],
) -> None:
    for record in records:
        source_link_id = str(record["source_link_id"])
        if session.get(CatalogStructureLinkRow, source_link_id) is not None:
            continue
        species_id = str(record["species_id"])
        published_structure_id = str(record["structure_id"])
        session.add(
            CatalogStructureLinkRow(
                source_link_id=source_link_id,
                species_id=species_id,
                application_species_id=species[species_id].application_id,
                source_package=str(record["source_package"]),
                source_id=str(record["source_id"]),
                published_structure_id=published_structure_id,
                application_structure_id=_stable_uuid(STRUCTURE_NAMESPACE, published_structure_id),
                relation=str(record["relation"]),
                evidence_refs=list(record["evidence_refs"]),
            )
        )


def _import_structure_records(session: Session, release: VerifiedRelease) -> int:
    referenced = {
        str(item["structure_id"]) for item in _load_jsonl(release, "structure_links.jsonl")
    }
    canonical_root = release.source_root / "packages" / "structure_registry" / "data" / "canonical"
    records: dict[str, dict[str, Any]] = {}
    filenames = (
        "ions.jsonl",
        "molecules.jsonl",
        "formula_units.jsonl",
        "polymer_repeat_units.jsonl",
    )
    for name in filenames:
        path = canonical_root / name
        if not path.is_file():
            raise ValueError(f"pinned structure registry 缺少 {name}")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            structure_id = str(record["structure_id"])
            if structure_id in referenced:
                records[structure_id] = record
    missing = sorted(referenced - records.keys())
    if missing:
        raise ValueError(f"accepted Structure links 缺少 registry records：{missing}")
    for structure_id, record in records.items():
        if session.get(CatalogStructureRecordRow, structure_id) is None:
            session.add(
                CatalogStructureRecordRow(
                    published_structure_id=structure_id,
                    structure_scope=str(record["structure_scope"]),
                    canonical_smiles=record.get("canonical_smiles"),
                    isomeric_smiles=record.get("isomeric_smiles"),
                    molecular_formula=record.get("molecular_formula"),
                    formal_charge=record.get("formal_charge"),
                    provenance=list(record.get("provenance", [])),
                )
            )
    return len(records)


def _import_knowledge_records(session: Session, records: list[dict[str, Any]]) -> int:
    imported = 0
    for record in records:
        source_type = str(record["source_type"])
        payload = dict(record["payload"])
        if (
            source_type not in {"concept", "phenomenon"}
            or payload.get("review_status") != "reviewed"
        ):
            continue
        consolidated_id = str(record["id"])
        if session.get(CatalogKnowledgeRecordRow, consolidated_id) is not None:
            imported += 1
            continue
        content = payload.get("definition_zh") or payload.get("observation_zh")
        if not isinstance(content, str) or not content.strip():
            continue
        session.add(
            CatalogKnowledgeRecordRow(
                consolidated_id=consolidated_id,
                application_id=_stable_uuid(KNOWLEDGE_NAMESPACE, consolidated_id),
                source_package=str(record["source_package"]),
                source_id=str(record["source_id"]),
                source_type=source_type,
                display_name_zh=str(record["display_name_zh"]),
                teaching_priority=str(record["teaching_priority"]),
                content_zh=content,
                related_reaction_ids=list(payload.get("related_reaction_ids", [])),
                related_species_ids=list(payload.get("related_species_ids", [])),
                payload=payload,
                provenance_refs=list(record["provenance_refs"]),
            )
        )
        imported += 1
    return imported


def _numeric_coefficient(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        coefficient = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return coefficient if coefficient > 0 else None


def _materialization_reasons(
    record: dict[str, Any], species: dict[str, CatalogSpeciesRow]
) -> tuple[str, ...]:
    reasons: set[str] = set()
    for participant in record["participants"]:
        if _numeric_coefficient(participant["coefficient"]) is None:
            reasons.add("symbolic_stoichiometry")
        species_id = participant.get("species_id")
        if species_id is None:
            reasons.add("non_species_participant")
        elif species_id not in species:
            reasons.add("unresolved_species")
        if participant["role"] not in {"reactant", "product"}:
            reasons.add("unsupported_participant_role")
    return tuple(sorted(reasons))


def _build_m05_document(
    record: dict[str, Any], species: dict[str, CatalogSpeciesRow]
) -> ReactionDocument:
    consolidated_id = str(record["id"])
    participants: list[ReactionParticipant] = []
    for ordinal, item in enumerate(record["participants"]):
        target_row = species[str(item["species_id"])]
        target = (
            IonId(target_row.application_id)
            if target_row.entity_kind == "ion"
            else SubstanceId(target_row.application_id)
        )
        coefficient = _numeric_coefficient(item["coefficient"])
        if coefficient is None:
            raise ValueError(f"不可物化的符号计量：{consolidated_id}")
        participants.append(
            ReactionParticipant(
                id=ReactionParticipantId(
                    _stable_uuid(PARTICIPANT_NAMESPACE, f"{consolidated_id}:{ordinal}")
                ),
                target=target,
                role=ReactionRole(str(item["role"])),
                stoichiometry=StoichiometricCoefficient(coefficient),
                phase=Phase(str(item["phase"])) if item.get("phase") else None,
            )
        )

    priority_heat = {
        "core": Decimal(1),
        "common": Decimal("0.5"),
        "extended": Decimal("0.25"),
    }
    reaction_types = list(record["reaction_types"])
    equation = record.get("equation")
    return ReactionDocument(
        reaction=Reaction(
            id=ReactionId(_stable_uuid(REACTION_NAMESPACE, consolidated_id)),
            code=ReactionCode(consolidated_id),
            participants=tuple(participants),
            conditions=tuple(
                Condition(kind="published_text", value=str(value)) for value in record["conditions"]
            ),
            status=ReactionStatus.REVIEW,
            reversible=bool(record.get("reversible")),
            provenance=(
                ProvenanceRef(
                    source_id=f"{record['source_package']}:{record['source_id']}",
                    citation=consolidated_id,
                    source_version=PINNED_RELEASE.release,
                ),
            ),
        ),
        equation_text=str(equation) if equation is not None else "",
        equation_mode=EquationMode.MOLECULAR,
        reaction_type=str(reaction_types[0] if reaction_types else "other"),
        exam_heat=priority_heat[str(record["teaching_priority"])],
        conservation_state="balanced"
        if record.get("equation_status") == "balanced_seed"
        else "invalid",
        phenomena=(),
        redox_metadata=None,
        reviewed_by=None,
        reviewed_at=None,
    )


def _import_reactions(
    session: Session,
    records: list[dict[str, Any]],
    species: dict[str, CatalogSpeciesRow],
) -> tuple[int, int]:
    repository = PostgresReactionRepository(session)
    materialized = 0
    catalog_only = 0
    for record in records:
        consolidated_id = str(record["id"])
        reasons = _materialization_reasons(record, species)
        state = "catalog_only" if reasons else "materialized"
        application_reaction_id = (
            None if reasons else _stable_uuid(REACTION_NAMESPACE, consolidated_id)
        )
        catalog_row = session.get(CatalogReactionRow, consolidated_id)
        if catalog_row is None:
            catalog_row = CatalogReactionRow(
                consolidated_id=consolidated_id,
                application_reaction_id=application_reaction_id,
                source_package=str(record["source_package"]),
                source_id=str(record["source_id"]),
                name_zh=str(record["name_zh"]),
                materialization_state=state,
                not_materialized_reasons=list(reasons),
                original_payload=record,
            )
            session.add(catalog_row)
            session.flush()
        elif catalog_row.materialization_state != state:
            raise ValueError(f"catalog Reaction materialization state 不可改变：{consolidated_id}")

        for ordinal, participant in enumerate(record["participants"]):
            key = (consolidated_id, ordinal)
            if session.get(CatalogReactionParticipantRow, key) is not None:
                continue
            species_id = participant.get("species_id")
            target_row = species.get(str(species_id)) if species_id is not None else None
            session.add(
                CatalogReactionParticipantRow(
                    reaction_id=consolidated_id,
                    ordinal=ordinal,
                    role=str(participant["role"]),
                    coefficient_text=str(participant["coefficient"]),
                    species_id=str(species_id) if species_id is not None else None,
                    application_target_id=(target_row.application_id if target_row else None),
                    target_type=(target_row.entity_kind if target_row else None),
                    non_species_ref=participant.get("non_species_ref"),
                    source_species_ref=str(participant["source_species_ref"]),
                    formula_literal=participant.get("formula_literal"),
                    phase=participant.get("phase"),
                )
            )

        if reasons:
            catalog_only += 1
            continue
        materialized += 1
        if session.get(ReactionRow, application_reaction_id) is None:
            repository.add(_build_m05_document(record, species))
    return materialized, catalog_only


def import_consolidated_release(
    session: Session,
    source_root: Path,
    *,
    source_identity: ReleaseSourceIdentity | None = None,
) -> KnowledgeCatalogImportResult:
    """Verify and import the pinned release without committing the caller's transaction."""

    release = verify_release(source_root, source_identity=source_identity)
    species_records = _load_jsonl(release, "species.jsonl")
    crosswalk_records = _load_jsonl(release, "crosswalk.jsonl")
    structure_link_records = _load_jsonl(release, "structure_links.jsonl")
    reaction_records = _load_jsonl(release, "reactions.jsonl")
    teaching_records = _load_jsonl(release, "teaching_projection.jsonl")
    knowledge_records = _load_jsonl(release, "knowledge_records.jsonl")

    _store_release(session, release)
    source_attribution_count = _import_source_attributions(session, release)
    species = _import_species(session, species_records)
    _import_crosswalks(session, crosswalk_records)
    _import_teaching_projections(session, teaching_records)
    _import_structure_links(session, structure_link_records, species)
    structure_record_count = _import_structure_records(session, release)
    knowledge_record_count = _import_knowledge_records(session, knowledge_records)
    session.flush()
    materialized, catalog_only = _import_reactions(session, reaction_records, species)
    session.flush()

    return KnowledgeCatalogImportResult(
        species_imported=len(species_records),
        teaching_projections_imported=len(teaching_records),
        structure_links_imported=len(structure_link_records),
        catalog_reactions_imported=len(reaction_records),
        m05_reactions_materialized=materialized,
        catalog_only_reactions=catalog_only,
        knowledge_records_imported=knowledge_record_count,
        structure_records_imported=structure_record_count,
        source_attributions_imported=source_attribution_count,
    )
