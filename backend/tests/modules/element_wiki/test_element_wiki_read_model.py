from datetime import UTC, datetime
from importlib import import_module
from uuid import UUID

import pytest
from pydantic import ValidationError


def test_build_element_wiki_projects_published_properties_sources_and_typed_empty_graph() -> None:
    read_model = import_module("chem_wiki.modules.element_wiki.read_model")
    periodic_table = import_module("chem_wiki.modules.periodic_table.read_model")
    element_id = UUID("12345678-1234-5678-1234-567812345678")
    element = periodic_table.build_periodic_table(
        [
            periodic_table.CanonicalElementSnapshot(
                id=element_id,
                atomic_number=17,
                symbol="Cl",
                name_zh="氯",
                name_en="chlorine",
                electronegativity=3.16,
                electronegativity_scale="Pauling",
                first_ionization_energy=12.968,
                first_ionization_energy_unit="eV",
            )
        ]
    )[0]
    source = read_model.PublishedFieldSource(
        field_name="first_ionization_energy",
        source_key="nist-asd",
        title="NIST Atomic Spectra Database",
        publisher="National Institute of Standards and Technology",
        url="https://physics.nist.gov/asd",
        license_code=None,
        retrieved_at=datetime(2026, 8, 24, tzinfo=UTC),
    )
    snapshot = read_model.CanonicalElementWikiSnapshot(
        atomic_weight_value=None,
        atomic_weight_lower=None,
        atomic_weight_upper=None,
        atomic_weight_uncertainty=None,
        electronegativity_value=3.16,
        electronegativity_scale="Pauling",
        first_ionization_energy_value=12.968,
        first_ionization_energy_unit="eV",
        atomic_radius_value=None,
        atomic_radius_unit=None,
        atomic_radius_qualifier=None,
        published_sources=(source,),
    )

    page = read_model.build_element_wiki(element, snapshot)

    assert page.identity.model_dump(by_alias=True) == {
        "id": element_id,
        "atomicNumber": 17,
        "symbol": "Cl",
        "nameZh": "氯",
        "nameEn": "chlorine",
        "status": "confirmed",
    }
    assert page.classification.model_dump() == {
        "category": "halogen",
        "period": 3,
        "group": 17,
        "block": "p",
    }
    properties = {item.key: item for item in page.properties}
    assert properties["atomicWeight"].status == "missing"
    assert properties["firstIonizationEnergy"].model_dump(by_alias=True) == {
        "key": "firstIonizationEnergy",
        "label": "第一电离能",
        "status": "available",
        "value": 12.968,
        "lower": None,
        "upper": None,
        "unit": "eV",
        "qualifier": None,
        "uncertainty": None,
        "sourceKeys": ["nist-asd"],
    }
    assert page.sources[0].model_dump(by_alias=True) == {
        "key": "nist-asd",
        "title": "NIST Atomic Spectra Database",
        "publisher": "National Institute of Standards and Technology",
        "url": "https://physics.nist.gov/asd",
        "licenseCode": None,
        "retrievedAt": datetime(2026, 8, 24, tzinfo=UTC),
        "fields": ["firstIonizationEnergy"],
    }
    assert page.sections.model_dump() == {
        "ions": [],
        "substances": [],
        "reactions": [],
        "phenomena": [],
        "concepts": [],
        "questions": [],
    }
    assert page.graph.model_dump(by_alias=True) == {
        "centerNodeId": element_id,
        "nodes": [
            {
                "id": element_id,
                "type": "Element",
                "label": "氯 Cl",
                "secondaryLabel": "原子序数 17",
                "href": f"/elements/{element_id}",
            }
        ],
        "edges": [],
        "emptyReason": "暂无已审核的相关物质、反应或概念数据",
    }


def test_unpublished_values_remain_missing_even_when_materialized_columns_are_non_null() -> None:
    read_model = import_module("chem_wiki.modules.element_wiki.read_model")
    periodic_table = import_module("chem_wiki.modules.periodic_table.read_model")
    element = periodic_table.build_periodic_table(
        [
            periodic_table.CanonicalElementSnapshot(
                id=UUID(int=2),
                atomic_number=2,
                symbol="He",
                name_zh="氦",
                name_en="helium",
                electronegativity=None,
                electronegativity_scale=None,
                first_ionization_energy=None,
                first_ionization_energy_unit=None,
            )
        ]
    )[0]
    snapshot = read_model.CanonicalElementWikiSnapshot(
        atomic_weight_value=4.0026,
        atomic_weight_lower=None,
        atomic_weight_upper=None,
        atomic_weight_uncertainty=None,
        electronegativity_value=None,
        electronegativity_scale=None,
        first_ionization_energy_value=None,
        first_ionization_energy_unit=None,
        atomic_radius_value=None,
        atomic_radius_unit=None,
        atomic_radius_qualifier=None,
        published_sources=(),
    )

    page = read_model.build_element_wiki(element, snapshot)

    atomic_weight = next(item for item in page.properties if item.key == "atomicWeight")
    assert atomic_weight.status == "missing"
    assert atomic_weight.value is None


def test_reaction_edges_require_an_explicit_reaction_node_endpoint() -> None:
    read_model = import_module("chem_wiki.modules.element_wiki.read_model")
    edge_id = UUID(int=1)
    substance_id = UUID(int=2)
    reaction_id = UUID(int=3)

    edge = read_model.KnowledgeEdge(
        id=edge_id,
        type="REACTANT_IN",
        source=substance_id,
        sourceType="Substance",
        target=reaction_id,
        targetType="Reaction",
        label="作为反应物参与",
    )

    assert edge.model_dump(by_alias=True) == {
        "id": edge_id,
        "type": "REACTANT_IN",
        "source": substance_id,
        "sourceType": "Substance",
        "target": reaction_id,
        "targetType": "Reaction",
        "label": "作为反应物参与",
    }
    with pytest.raises(ValidationError, match="REACTANT_IN requires Substance -> Reaction"):
        read_model.KnowledgeEdge(
            id=edge_id,
            type="REACTANT_IN",
            source=substance_id,
            sourceType="Substance",
            target=reaction_id,
            targetType="Substance",
            label="错误的物质直连",
        )


def test_element_wiki_classification_rejects_categories_outside_the_m03_contract() -> None:
    read_model = import_module("chem_wiki.modules.element_wiki.read_model")

    with pytest.raises(ValidationError):
        read_model.ElementWikiClassification(
            category="unknown-category",
            period=3,
            group=17,
            block="p",
        )
