import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.main import create_app
from chem_wiki.modules.element_data import ElementDataBase, bootstrap_element_identities
from chem_wiki.modules.element_wiki import PostgresElementWikiReader
from chem_wiki.modules.knowledge_catalog import (
    CatalogKnowledgeRecordRow,
    CatalogReactionParticipantRow,
    CatalogReactionRow,
    CatalogSourceAttributionRow,
    CatalogSourceCrosswalkRow,
    CatalogSpeciesRow,
    CatalogStructureLinkRow,
    CatalogStructureRecordRow,
    CatalogTeachingProjectionRow,
    PostgresCatalogReader,
    import_consolidated_release,
)
from chem_wiki.modules.periodic_table import PostgresPeriodicTableReader
from chem_wiki.modules.reaction_core import ReactionParticipantRow, ReactionRow

pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def consolidated_source() -> Path:
    configured = os.environ.get("KNOWLEDGE_CATALOG_SOURCE")
    if not configured:
        pytest.skip("KNOWLEDGE_CATALOG_SOURCE is required for consolidated release integration")
    source = Path(configured)
    if not source.is_dir():
        pytest.fail(f"KNOWLEDGE_CATALOG_SOURCE does not exist: {source}")
    return source


@contextmanager
def _migrated_engine() -> Iterator[Engine]:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    engine = create_engine(Settings().database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    try:
        yield engine
    finally:
        command.downgrade(config, "base")
        engine.dispose()


def _count(session: Session, row_type: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(row_type)) or 0


def test_release_import_is_complete_idempotent_and_queryable(
    consolidated_source: Path,
) -> None:
    with _migrated_engine() as engine, Session(engine) as session:
        bootstrap_element_identities(session)
        first = import_consolidated_release(session, consolidated_source)
        session.commit()
        ids_after_first = dict(
            session.execute(
                select(CatalogSpeciesRow.consolidated_id, CatalogSpeciesRow.application_id)
            ).all()
        )

        assert first.species_imported == 309
        assert first.teaching_projections_imported == 309
        assert first.structure_links_imported == 69
        assert first.catalog_reactions_imported == 183
        assert first.m05_reactions_materialized == 175
        assert first.catalog_only_reactions == 8
        assert first.knowledge_records_imported == 127
        assert first.structure_records_imported == 69
        assert first.source_attributions_imported == 7
        assert _count(session, CatalogSpeciesRow) == 309
        assert _count(session, CatalogSourceCrosswalkRow) == 309
        assert _count(session, CatalogSourceAttributionRow) == 7
        assert _count(session, CatalogTeachingProjectionRow) == 309
        assert _count(session, CatalogStructureLinkRow) == 69
        assert _count(session, CatalogStructureRecordRow) == 69
        assert _count(session, CatalogKnowledgeRecordRow) == 127
        assert _count(session, CatalogReactionRow) == 183
        assert _count(session, ReactionRow) == 175

        catalog_only = session.scalars(
            select(CatalogReactionRow).where(
                CatalogReactionRow.materialization_state == "catalog_only"
            )
        ).all()
        assert len(catalog_only) == 8
        assert all("symbolic_stoichiometry" in row.not_materialized_reasons for row in catalog_only)
        phenol_resin = next(
            row
            for row in catalog_only
            if row.consolidated_id
            == "reaction:organic:org-reaction:phenol-formaldehyde-condensation"
        )
        assert "non_species_participant" in phenol_resin.not_materialized_reasons
        assert phenol_resin.original_payload["participants"][0]["coefficient"] == "n"
        assert phenol_resin.original_payload["participants"][2]["non_species_ref"] == (
            "organic-material:phenol-formaldehyde-resin"
        )

        materialized_participants = session.scalars(
            select(CatalogReactionParticipantRow)
            .join(CatalogReactionRow)
            .where(CatalogReactionRow.materialization_state == "materialized")
        ).all()
        assert materialized_participants
        assert all(item.application_target_id is not None for item in materialized_participants)
        application_ids = set(ids_after_first.values())
        assert set(session.scalars(select(ReactionParticipantRow.target_id))) <= application_ids

        second = import_consolidated_release(session, consolidated_source)
        session.commit()
        assert second.catalog_reactions_imported == 183
        assert second.m05_reactions_materialized == 175
        assert _count(session, CatalogSpeciesRow) == 309
        assert _count(session, CatalogReactionRow) == 183
        assert _count(session, ReactionRow) == 175
        assert (
            dict(
                session.execute(
                    select(CatalogSpeciesRow.consolidated_id, CatalogSpeciesRow.application_id)
                ).all()
            )
            == ids_after_first
        )
        assert all(isinstance(value, UUID) for value in ids_after_first.values())

        reader = PostgresCatalogReader(session)
        sodium = reader.search_species(query="钠离子", limit=1)[0]
        structure = reader.get_structure_entry(sodium.application_id)
        assert structure is not None
        assert structure.canonical_smiles == "[Na+]"
        sodium_element_id = session.scalar(
            select(ElementDataBase.metadata.tables["element"].c.id).where(
                ElementDataBase.metadata.tables["element"].c.atomic_number == 11
            )
        )
        assert sodium_element_id is not None
        sodium_page = PostgresElementWikiReader(
            session,
            PostgresPeriodicTableReader(session),
            reader,
        ).get_element(sodium_element_id)
        assert sodium_page is not None
        assert sodium_page.sections.ions
        assert sodium_page.sections.substances
        assert sodium_page.sections.reactions
        assert sodium_page.sections.concepts
        assert sodium_page.sections.phenomena
        assert any(
            node.href and node.href.startswith("/equation-lab?reaction=")
            for node in sodium_page.sections.reactions
        )
        assert any(
            node.href and node.href.startswith("/structure-lab?species=")
            for node in [*sodium_page.sections.ions, *sodium_page.sections.substances]
        )
        assert reader.search_species(query="硫酸", limit=5)[0].name_zh == "硫酸"
        assert reader.search_species(query="硫酸根", limit=5)[0].name_zh == "硫酸根离子"
        assert reader.search_species(query="sulfate", limit=5)[0].name_zh == "硫酸根离子"
        assert reader.search_species(query="SO4", limit=5)[0].formula == "SO4"
        assert all(
            item.primary_category == "acid"
            for item in reader.search_species(primary_category="acid", limit=50)
        )
        assert (
            reader.search_species(query="Fe", equation_mode="molecular", limit=5)[0].entity_kind
            == "substance"
        )
        assert (
            reader.search_species(query="Fe", equation_mode="ionic", limit=5)[0].entity_kind
            == "ion"
        )
        assert reader.search_species(query="不存在的目录项", limit=5) == []
        assert len(reader.search_species(query="Fe", limit=1)) == 1
        assert len(reader.search_species(query="Fe", limit=20)) > 1

        strontium_completions = reader.complete_species(composition={"Sr": 1}, limit=20)
        assert len(strontium_completions) > 1
        assert all(item.entity_kind == "substance" for item in strontium_completions)
        assert all(item.composition and "Sr" in item.composition for item in strontium_completions)
        assert reader.complete_species(
            composition={"Sr": 1, "S": 1, "O": 4}, limit=20
        )[0].formula == "SrSO4"
        assert reader.complete_species(
            composition={"Na": 2, "S": 1, "O": 4}, limit=20
        )[0].formula == "Na2SO4"
        assert reader.complete_species(composition={"Xe": 99}, limit=20) == []

        detail = reader.get_reaction_detail("reaction:inorganic:reaction:agno3-nacl")
        assert detail is not None
        assert detail.concepts
        assert detail.phenomena
        assert detail.related_species
        assert any(
            item.display_name_zh == "氯化银沉淀" and item.content_zh == "生成白色沉淀。"
            for item in detail.phenomena
        )
        assert any(item.url and "moe.gov.cn" in item.url for item in detail.sources)
        assert all("src:" not in item.name for item in detail.sources)

        catalog_reaction = reader.get_reaction(phenol_resin.consolidated_id)
        assert catalog_reaction is not None
        assert catalog_reaction.materialization_state == "catalog_only"
        assert "non_species_participant" in catalog_reaction.not_materialized_reasons
        assert catalog_reaction.participants[0].coefficient == "n"
        assert catalog_reaction.participants[2].non_species_ref == (
            "organic-material:phenol-formaldehyde-resin"
        )
        mapped_participant = next(
            participant
            for participant in catalog_reaction.participants
            if participant.application_target_id is not None
        )
        assert mapped_participant.name_zh
        assert mapped_participant.formula
        related_reactions = reader.find_reactions_by_application_ids(
            [mapped_participant.application_target_id]
        )
        assert related_reactions
        assert all(
            any(
                participant.application_target_id == mapped_participant.application_target_id
                for participant in reaction.participants
            )
            for reaction in related_reactions
        )

        response = TestClient(create_app()).get(
            "/v1/catalog/species",
            params={"q": "Fe", "equation_mode": "ionic", "limit": 5},
        )
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) > 1
        assert payload[0]["entityKind"] == "ion"
        assert UUID(payload[0]["applicationId"])

        completion_response = TestClient(create_app()).get(
            "/v1/catalog/species/completions",
            params={"composition": '{"Sr":1,"S":1,"O":4}', "limit": 20},
        )
        assert completion_response.status_code == 200
        assert completion_response.json()[0]["formula"] == "SrSO4"

        reaction_response = TestClient(create_app()).get(
            f"/v1/catalog/reactions/{phenol_resin.consolidated_id}"
        )
        assert reaction_response.status_code == 200
        assert reaction_response.json()["materializationState"] == "catalog_only"

        detail_response = TestClient(create_app()).get(
            "/v1/catalog/reactions/reaction:inorganic:reaction:agno3-nacl/detail"
        )
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["concepts"]
        assert detail_payload["phenomena"]
        assert detail_payload["relatedSpecies"]
        assert detail_payload["sources"]
