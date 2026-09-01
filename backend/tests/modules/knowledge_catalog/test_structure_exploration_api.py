from uuid import UUID

from fastapi.testclient import TestClient

from chem_wiki.main import create_app
from chem_wiki.modules.knowledge_catalog import get_catalog_reader


class StructureExplorationReaderStub:
    def get_structure_exploration(self, application_species_id: UUID):
        if application_species_id == UUID(int=2):
            return {
                "species": {
                    "consolidatedId": "species:ethene",
                    "applicationId": str(application_species_id),
                    "entityKind": "substance",
                    "nameZh": "乙烯",
                    "nameEn": "ethene",
                    "formula": "C2H4",
                    "charge": 0,
                    "composition": {"C": 2, "H": 4},
                    "aliases": [],
                    "chemicalClassifications": ["alkene"],
                    "primaryCategory": "organic",
                    "tags": [],
                    "defaultPriority": "core",
                    "defaultPaletteRank": 1,
                    "equationModes": {
                        "molecular": "recommended",
                        "ionic": "deemphasized",
                        "netIonic": "deemphasized",
                    },
                },
                "structure": {
                    "applicationSpeciesId": str(application_species_id),
                    "publishedStructureId": "structure:ethene",
                    "structureScope": "molecule",
                    "canonicalSmiles": "C=C",
                    "isomericSmiles": "C=C",
                    "molecularFormula": "C2H4",
                    "formalCharge": 0,
                },
                "knowledge": [
                    {
                        "consolidatedId": "knowledge:ethene",
                        "applicationId": str(UUID(int=3)),
                        "sourcePackage": "structural_chemistry",
                        "sourceId": "ethene",
                        "sourceType": "molecular_example",
                        "displayNameZh": "乙烯",
                        "teachingPriority": "core",
                        "contentZh": None,
                        "relatedReactionIds": [],
                        "relatedSpeciesIds": [],
                        "payload": {"molecular_geometry": "planar_molecule"},
                        "links": [],
                        "provenanceRefs": [],
                        "sources": [],
                    }
                ],
                "relatedSpecies": [],
                "relatedReactions": [
                    {
                        "consolidatedId": "reaction:ethene-bromine-addition",
                        "applicationReactionId": str(UUID(int=4)),
                        "sourcePackage": "organic",
                        "sourceId": "ethene-bromine-addition",
                        "nameZh": "乙烯与溴的加成反应",
                        "materializationState": "materialized",
                        "notMaterializedReasons": [],
                        "participants": [],
                        "reactionTypes": ["addition"],
                        "conditions": [],
                        "equation": "C2H4 + Br2 -> C2H4Br2",
                        "equationStatus": "canonical",
                        "reversible": False,
                        "provenanceRefs": [],
                    }
                ],
            }
        if application_species_id == UUID(int=5):
            return {
                "species": {
                    "consolidatedId": "species:aluminium-nitrate",
                    "applicationId": str(application_species_id),
                    "entityKind": "substance",
                    "nameZh": "硝酸铝",
                    "nameEn": None,
                    "formula": "Al(NO3)3",
                    "charge": 0,
                    "composition": {"Al": 1, "N": 3, "O": 9},
                    "aliases": [],
                    "chemicalClassifications": ["salt"],
                    "primaryCategory": "salt",
                    "tags": [],
                    "defaultPriority": "common",
                    "defaultPaletteRank": 2,
                    "equationModes": {
                        "molecular": "available",
                        "ionic": "available",
                        "netIonic": "available",
                    },
                },
                "structure": None,
                "knowledge": [],
                "relatedSpecies": [],
                "relatedReactions": [],
            }
        return None


def test_structure_exploration_endpoint_projects_catalog_context_and_keeps_missing_structure_explicit() -> (
    None
):
    reader = StructureExplorationReaderStub()
    app = create_app()
    app.dependency_overrides[get_catalog_reader] = lambda: reader
    client = TestClient(app)

    ethene = client.get(f"/v1/catalog/species/{UUID(int=2)}/structure-exploration")
    unavailable = client.get(f"/v1/catalog/species/{UUID(int=5)}/structure-exploration")

    assert ethene.status_code == 200
    assert ethene.json()["species"]["nameZh"] == "乙烯"
    assert ethene.json()["structure"]["canonicalSmiles"] == "C=C"
    assert ethene.json()["knowledge"][0]["payload"]["molecular_geometry"] == "planar_molecule"
    assert ethene.json()["relatedReactions"][0]["materializationState"] == "materialized"
    assert unavailable.status_code == 200
    assert unavailable.json()["species"]["nameZh"] == "硝酸铝"
    assert unavailable.json()["structure"] is None
