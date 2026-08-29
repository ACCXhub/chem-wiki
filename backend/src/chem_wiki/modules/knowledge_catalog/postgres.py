"""PostgreSQL catalog query adapter for the bounded consolidated dataset."""

import unicodedata
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .persistence import (
    CatalogKnowledgeRecordRow,
    CatalogReactionParticipantRow,
    CatalogReactionRow,
    CatalogSourceAttributionRow,
    CatalogSpeciesRow,
    CatalogStructureLinkRow,
    CatalogStructureRecordRow,
    CatalogTeachingProjectionRow,
)
from .read_model import (
    CatalogKnowledgeResult,
    CatalogReactionDetail,
    CatalogReactionParticipantResult,
    CatalogReactionResult,
    CatalogRelatedSpeciesResult,
    CatalogSourceAttributionResult,
    CatalogSpeciesResult,
    CatalogStructureEntry,
)

EQUATION_MODES = {"molecular", "ionic", "net_ionic"}
SUITABILITY_RANK = {"recommended": 0, "available": 1, "deemphasized": 2}
TEACHING_PRIORITY_RANK = {"core": 0, "common": 1, "extended": 2}


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _match_rank(
    species: CatalogSpeciesRow,
    projection: CatalogTeachingProjectionRow,
    query: str,
) -> int | None:
    if not query:
        return 0
    name_zh = _normalize(species.name_zh)
    name_en = _normalize(species.name_en or "")
    formula = _normalize(species.formula)
    aliases = [_normalize(value) for value in species.aliases]
    tokens = [_normalize(value) for value in projection.search_tokens]
    if query == name_zh:
        return 0
    if query in aliases:
        return 1
    if query == name_en:
        return 2
    if query == formula:
        return 3
    if query in tokens:
        return 4
    searchable = [name_zh, name_en, formula, *aliases, *tokens]
    if any(value.startswith(query) for value in searchable):
        return 5
    if any(query in value for value in searchable):
        return 6
    return None


def _equation_suitability(projection: CatalogTeachingProjectionRow, mode: str) -> str:
    return {
        "molecular": projection.molecular_suitability,
        "ionic": projection.ionic_suitability,
        "net_ionic": projection.net_ionic_suitability,
    }[mode]


class PostgresCatalogReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def search_species(
        self,
        *,
        query: str = "",
        primary_category: str | None = None,
        equation_mode: str | None = None,
        composition: dict[str, int] | None = None,
        total_charge: int | None = None,
        entity_kind: Literal["ion", "substance"] | None = None,
        application_ids: list[UUID] | None = None,
        limit: int = 20,
    ) -> list[CatalogSpeciesResult]:
        if not 1 <= limit <= 50:
            raise ValueError("catalog result limit 必须在 1 到 50 之间")
        if equation_mode is not None and equation_mode not in EQUATION_MODES:
            raise ValueError("不支持的 equation mode")

        application_id_set = set(application_ids) if application_ids is not None else None

        statement = select(CatalogSpeciesRow, CatalogTeachingProjectionRow).join(
            CatalogTeachingProjectionRow,
            CatalogTeachingProjectionRow.species_id == CatalogSpeciesRow.consolidated_id,
        )
        if application_id_set is not None:
            statement = statement.where(CatalogSpeciesRow.application_id.in_(application_id_set))
        if primary_category is not None:
            statement = statement.where(
                CatalogTeachingProjectionRow.primary_category == primary_category
            )
        normalized_query = _normalize(query)
        ranked: list[
            tuple[int, int, int, str, CatalogSpeciesRow, CatalogTeachingProjectionRow]
        ] = []
        for species, projection in self._session.execute(statement):
            if application_id_set is not None and species.application_id not in application_id_set:
                continue
            if composition is not None and species.composition != composition:
                continue
            if total_charge is not None and species.charge != total_charge:
                continue
            if entity_kind is not None and species.entity_kind != entity_kind:
                continue
            match_rank = _match_rank(species, projection, normalized_query)
            if match_rank is None:
                continue
            suitability_rank = (
                SUITABILITY_RANK[_equation_suitability(projection, equation_mode)]
                if equation_mode
                else 0
            )
            ranked.append(
                (
                    suitability_rank,
                    match_rank,
                    projection.default_palette_rank,
                    species.consolidated_id,
                    species,
                    projection,
                )
            )
        ranked.sort(key=lambda item: item[:4])
        return [
            CatalogSpeciesResult(
                consolidated_id=species.consolidated_id,
                application_id=species.application_id,
                entity_kind=species.entity_kind,
                name_zh=species.name_zh,
                name_en=species.name_en,
                formula=species.formula,
                charge=species.charge,
                composition=species.composition,
                aliases=species.aliases,
                chemical_classifications=species.chemical_classifications,
                primary_category=projection.primary_category,
                tags=projection.tags,
                default_priority=projection.default_priority,
                default_palette_rank=projection.default_palette_rank,
                equation_modes={
                    "molecular": projection.molecular_suitability,
                    "ionic": projection.ionic_suitability,
                    "net_ionic": projection.net_ionic_suitability,
                },
            )
            for _, _, _, _, species, projection in ranked[:limit]
        ]

    def complete_species(
        self,
        *,
        composition: dict[str, int],
        equation_mode: str | None = None,
        entity_kind: Literal["ion", "substance"] = "substance",
        limit: int = 20,
    ) -> list[CatalogSpeciesResult]:
        if not composition or any(count <= 0 for count in composition.values()):
            raise ValueError("completion composition 必须包含正整数元素计数")
        if not 1 <= limit <= 50:
            raise ValueError("catalog result limit 必须在 1 到 50 之间")
        if equation_mode is not None and equation_mode not in EQUATION_MODES:
            raise ValueError("不支持的 equation mode")

        statement = (
            select(CatalogSpeciesRow, CatalogTeachingProjectionRow)
            .join(
                CatalogTeachingProjectionRow,
                CatalogTeachingProjectionRow.species_id == CatalogSpeciesRow.consolidated_id,
            )
            .where(CatalogSpeciesRow.entity_kind == entity_kind)
        )
        ranked: list[
            tuple[
                int,
                int,
                int,
                int,
                int,
                int,
                int,
                int,
                str,
                CatalogSpeciesRow,
                CatalogTeachingProjectionRow,
            ]
        ] = []
        selected_elements = set(composition)
        for species, projection in self._session.execute(statement):
            candidate = species.composition
            if species.entity_kind != entity_kind or not candidate:
                continue
            if not selected_elements <= set(candidate):
                continue
            exact_rank = 0 if candidate == composition else 1
            deficit = sum(max(composition[element] - candidate[element], 0) for element in composition)
            count_satisfaction_rank = 0 if deficit == 0 else 1
            extra_elements = len(set(candidate) - selected_elements)
            extra_atoms = sum(
                max(count - composition.get(element, 0), 0)
                for element, count in candidate.items()
            )
            suitability_rank = (
                SUITABILITY_RANK[_equation_suitability(projection, equation_mode)]
                if equation_mode
                else 0
            )
            ranked.append(
                (
                    exact_rank,
                    count_satisfaction_rank,
                    deficit,
                    extra_elements,
                    extra_atoms,
                    suitability_rank,
                    TEACHING_PRIORITY_RANK.get(projection.default_priority, 9),
                    projection.default_palette_rank,
                    species.consolidated_id,
                    species,
                    projection,
                )
            )
        ranked.sort(key=lambda item: item[:9])
        return [
            CatalogSpeciesResult(
                consolidated_id=species.consolidated_id,
                application_id=species.application_id,
                entity_kind=species.entity_kind,
                name_zh=species.name_zh,
                name_en=species.name_en,
                formula=species.formula,
                charge=species.charge,
                composition=species.composition,
                aliases=species.aliases,
                chemical_classifications=species.chemical_classifications,
                primary_category=projection.primary_category,
                tags=projection.tags,
                default_priority=projection.default_priority,
                default_palette_rank=projection.default_palette_rank,
                equation_modes={
                    "molecular": projection.molecular_suitability,
                    "ionic": projection.ionic_suitability,
                    "net_ionic": projection.net_ionic_suitability,
                },
            )
            for *_, species, projection in ranked[:limit]
        ]

    def get_reaction(self, consolidated_id: str) -> CatalogReactionResult | None:
        row = self._session.get(CatalogReactionRow, consolidated_id)
        if row is None:
            return None
        participant_rows = self._session.execute(
            select(CatalogReactionParticipantRow, CatalogSpeciesRow)
            .outerjoin(
                CatalogSpeciesRow,
                CatalogSpeciesRow.consolidated_id == CatalogReactionParticipantRow.species_id,
            )
            .where(CatalogReactionParticipantRow.reaction_id == consolidated_id)
            .order_by(CatalogReactionParticipantRow.ordinal)
        ).all()
        source_participants = list(row.original_payload["participants"])
        participants = [
            CatalogReactionParticipantResult(
                role=participant_row.role,
                coefficient=source_participants[participant_row.ordinal]["coefficient"],
                species_id=participant_row.species_id,
                application_target_id=participant_row.application_target_id,
                target_type=participant_row.target_type,
                non_species_ref=participant_row.non_species_ref,
                source_species_ref=participant_row.source_species_ref,
                formula_literal=participant_row.formula_literal,
                phase=participant_row.phase,
                name_zh=species_row.name_zh if species_row is not None else None,
                formula=(
                    species_row.formula
                    if species_row is not None
                    else participant_row.formula_literal
                ),
                charge=species_row.charge if species_row is not None else None,
            )
            for participant_row, species_row in participant_rows
        ]
        return CatalogReactionResult(
            consolidated_id=row.consolidated_id,
            application_reaction_id=row.application_reaction_id,
            source_package=row.source_package,
            source_id=row.source_id,
            name_zh=row.name_zh,
            materialization_state=row.materialization_state,
            not_materialized_reasons=row.not_materialized_reasons,
            participants=participants,
            reaction_types=list(row.original_payload["reaction_types"]),
            conditions=list(row.original_payload["conditions"]),
            equation=row.original_payload.get("equation"),
            equation_status=row.original_payload.get("equation_status"),
            reversible=row.original_payload.get("reversible"),
            provenance_refs=list(row.original_payload["provenance_refs"]),
        )

    def get_species_by_consolidated_ids(
        self, consolidated_ids: list[str]
    ) -> list[CatalogSpeciesResult]:
        order = {value: index for index, value in enumerate(consolidated_ids)}
        if not order:
            return []
        rows = self._session.execute(
            select(CatalogSpeciesRow, CatalogTeachingProjectionRow)
            .join(
                CatalogTeachingProjectionRow,
                CatalogTeachingProjectionRow.species_id == CatalogSpeciesRow.consolidated_id,
            )
            .where(CatalogSpeciesRow.consolidated_id.in_(order))
        ).all()
        rows.sort(key=lambda item: order[item[0].consolidated_id])
        return [
            CatalogSpeciesResult(
                consolidated_id=species.consolidated_id,
                application_id=species.application_id,
                entity_kind=species.entity_kind,
                name_zh=species.name_zh,
                name_en=species.name_en,
                formula=species.formula,
                charge=species.charge,
                composition=species.composition,
                aliases=species.aliases,
                chemical_classifications=species.chemical_classifications,
                primary_category=projection.primary_category,
                tags=projection.tags,
                default_priority=projection.default_priority,
                default_palette_rank=projection.default_palette_rank,
                equation_modes={
                    "molecular": projection.molecular_suitability,
                    "ionic": projection.ionic_suitability,
                    "net_ionic": projection.net_ionic_suitability,
                },
            )
            for species, projection in rows
        ]

    def get_reaction_detail(self, consolidated_id: str) -> CatalogReactionDetail | None:
        reaction = self.get_reaction(consolidated_id)
        if reaction is None:
            return None
        knowledge = self.find_knowledge_for_reactions([reaction])
        participant_species_ids = list(
            dict.fromkeys(
                participant.species_id
                for participant in reaction.participants
                if participant.species_id is not None
            )
        )
        related_species = [
            CatalogRelatedSpeciesResult(
                **species.model_dump(),
                structure_available=self.get_structure_entry(species.application_id) is not None,
            )
            for species in self.get_species_by_consolidated_ids(participant_species_ids)
        ]
        source_rows = self._session.scalars(
            select(CatalogSourceAttributionRow)
            .where(CatalogSourceAttributionRow.source_ref.in_(reaction.provenance_refs))
            .order_by(CatalogSourceAttributionRow.source_ref)
        ).all()
        return CatalogReactionDetail(
            **reaction.model_dump(),
            concepts=[item for item in knowledge if item.source_type == "concept"],
            phenomena=[item for item in knowledge if item.source_type == "phenomenon"],
            related_species=related_species,
            sources=[
                CatalogSourceAttributionResult(name=row.name, url=row.url) for row in source_rows
            ],
        )

    def get_reactions_by_consolidated_ids(
        self, consolidated_ids: list[str]
    ) -> list[CatalogReactionResult]:
        return [
            reaction
            for consolidated_id in consolidated_ids
            if (reaction := self.get_reaction(consolidated_id)) is not None
        ]

    def find_knowledge_for_reactions(
        self, reactions: list[CatalogReactionResult]
    ) -> list[CatalogKnowledgeResult]:
        source_keys = {(item.source_package, item.source_id) for item in reactions}
        if not source_keys:
            return []
        rows = self._session.scalars(select(CatalogKnowledgeRecordRow)).all()
        priority = {"core": 0, "common": 1, "extended": 2}
        matched = [
            row
            for row in rows
            if any(
                (row.source_package, related_id) in source_keys
                for related_id in row.related_reaction_ids
            )
        ]
        matched.sort(
            key=lambda row: (
                priority.get(row.teaching_priority, 9),
                row.source_type,
                row.consolidated_id,
            )
        )
        return [
            CatalogKnowledgeResult(
                consolidated_id=row.consolidated_id,
                application_id=row.application_id,
                source_type=row.source_type,
                display_name_zh=row.display_name_zh,
                teaching_priority=row.teaching_priority,
                content_zh=row.content_zh,
                related_reaction_ids=list(row.related_reaction_ids),
                related_species_ids=list(row.related_species_ids),
            )
            for row in matched
        ]

    def get_structure_entry(self, application_species_id: UUID) -> CatalogStructureEntry | None:
        row = self._session.execute(
            select(CatalogStructureLinkRow, CatalogStructureRecordRow)
            .join(
                CatalogStructureRecordRow,
                CatalogStructureRecordRow.published_structure_id
                == CatalogStructureLinkRow.published_structure_id,
            )
            .where(CatalogStructureLinkRow.application_species_id == application_species_id)
            .order_by(CatalogStructureLinkRow.source_link_id)
        ).first()
        if row is None:
            return None
        link, structure = row
        return CatalogStructureEntry(
            application_species_id=link.application_species_id,
            published_structure_id=structure.published_structure_id,
            structure_scope=structure.structure_scope,
            canonical_smiles=structure.canonical_smiles,
            isomeric_smiles=structure.isomeric_smiles,
            molecular_formula=structure.molecular_formula,
            formal_charge=structure.formal_charge,
        )

    def find_reactions_by_application_ids(
        self, application_ids: list[UUID]
    ) -> list[CatalogReactionResult]:
        identities = sorted(set(application_ids), key=str)
        if not identities:
            return []
        reaction_ids = self._session.scalars(
            select(CatalogReactionParticipantRow.reaction_id)
            .where(CatalogReactionParticipantRow.application_target_id.in_(identities))
            .distinct()
            .order_by(CatalogReactionParticipantRow.reaction_id)
        ).all()
        reactions = [self.get_reaction(reaction_id) for reaction_id in reaction_ids]
        return [reaction for reaction in reactions if reaction is not None]
