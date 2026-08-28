from uuid import UUID

from fastapi.testclient import TestClient

from chem_wiki.main import create_app
from chem_wiki.modules.knowledge_catalog import (
    CatalogReactionParticipantResult,
    CatalogReactionResult,
    get_catalog_reader,
)


class CatalogReaderStub:
    def __init__(self) -> None:
        self.requested_ids: list[UUID] = []

    def find_reactions_by_application_ids(
        self, application_ids: list[UUID]
    ) -> list[CatalogReactionResult]:
        self.requested_ids = application_ids
        return [
            CatalogReactionResult(
                consolidated_id="reaction:water",
                application_reaction_id=UUID(int=20),
                source_package="curated",
                source_id="water",
                name_zh="水的生成",
                materialization_state="materialized",
                not_materialized_reasons=[],
                participants=[
                    CatalogReactionParticipantResult(
                        role="reactant",
                        coefficient=2,
                        species_id="species:hydrogen",
                        application_target_id=UUID(int=1),
                        target_type="substance",
                        non_species_ref=None,
                        source_species_ref="hydrogen",
                        formula_literal="H2",
                        phase="g",
                        name_zh="氢气",
                        formula="H2",
                        charge=0,
                    )
                ],
                reaction_types=["combination"],
                conditions=["点燃"],
                equation="2H2 + O2 -> 2H2O",
                equation_status="canonical",
                reversible=False,
                provenance_refs=["source:water"],
            )
        ]


def test_candidate_endpoint_uses_structured_anchors_and_returns_m07_projection() -> None:
    reader = CatalogReaderStub()
    app = create_app()
    app.dependency_overrides[get_catalog_reader] = lambda: reader

    response = TestClient(app).post(
        "/v1/reaction-builder/candidates",
        json={
            "reactantApplicationIds": [str(UUID(int=1))],
            "productApplicationIds": [],
        },
    )

    assert response.status_code == 200
    assert reader.requested_ids == [UUID(int=1)]
    candidate = response.json()["candidates"][0]
    assert candidate["consolidatedId"] == "reaction:water"
    assert candidate["matchedAnchorCount"] == 1
    assert candidate["missingParticipantCount"] == 0
    assert candidate["participants"][0]["nameZh"] == "氢气"
    assert candidate["participants"][0]["coefficient"] == 2
