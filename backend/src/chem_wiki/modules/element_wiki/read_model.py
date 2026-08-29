"""M04 Element Wiki and element-centred knowledge graph read model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from chem_wiki.modules.knowledge_catalog import (
    CatalogKnowledgeResult,
    CatalogReactionResult,
    CatalogSpeciesResult,
    CatalogStructureEntry,
)
from chem_wiki.modules.periodic_table import ElementCategory, PeriodicTableElement

PropertyKey = Literal[
    "atomicWeight",
    "electronegativity",
    "firstIonizationEnergy",
    "atomicRadius",
]
NodeType = Literal[
    "Element",
    "Ion",
    "Substance",
    "Reaction",
    "Phenomenon",
    "Concept",
    "Question",
]
EdgeType = Literal[
    "CONTAINS_ELEMENT",
    "REACTANT_IN",
    "PRODUCT_OF",
    "HAS_PHENOMENON",
    "RELATES_TO",
    "TESTS",
]

_PROPERTY_ALIASES: dict[str, PropertyKey] = {
    "atomic_weight": "atomicWeight",
    "electronegativity": "electronegativity",
    "first_ionization_energy": "firstIonizationEnergy",
    "atomic_radius": "atomicRadius",
}


@dataclass(frozen=True, slots=True)
class PublishedFieldSource:
    field_name: str
    source_key: str
    title: str
    publisher: str | None
    url: str | None
    license_code: str | None
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class CanonicalElementWikiSnapshot:
    atomic_weight_value: float | None
    atomic_weight_lower: float | None
    atomic_weight_upper: float | None
    atomic_weight_uncertainty: float | None
    electronegativity_value: float | None
    electronegativity_scale: str | None
    first_ionization_energy_value: float | None
    first_ionization_energy_unit: str | None
    atomic_radius_value: float | None
    atomic_radius_unit: str | None
    atomic_radius_qualifier: str | None
    published_sources: tuple[PublishedFieldSource, ...]


class ElementWikiIdentity(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    atomic_number: int = Field(alias="atomicNumber")
    symbol: str
    name_zh: str = Field(alias="nameZh")
    name_en: str = Field(alias="nameEn")
    status: Literal["confirmed", "predicted"]


class ElementWikiClassification(BaseModel):
    category: ElementCategory
    period: int
    group: int | None
    block: Literal["s", "p", "d", "f"]


class ElementWikiProperty(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: PropertyKey
    label: str
    status: Literal["available", "missing"]
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    unit: str | None = None
    qualifier: str | None = None
    uncertainty: float | None = None
    source_keys: list[str] = Field(alias="sourceKeys")


class ElementWikiSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    title: str
    publisher: str | None
    url: str | None
    license_code: str | None = Field(alias="licenseCode")
    retrieved_at: datetime = Field(alias="retrievedAt")
    fields: list[str]


class KnowledgeNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    type: NodeType
    label: str
    secondary_label: str | None = Field(default=None, alias="secondaryLabel")
    href: str | None = None
    description: str | None = None


class KnowledgeEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    type: EdgeType
    source: UUID
    source_type: NodeType = Field(alias="sourceType")
    target: UUID
    target_type: NodeType = Field(alias="targetType")
    label: str

    @model_validator(mode="after")
    def validate_typed_endpoints(self) -> "KnowledgeEdge":
        pair = (self.source_type, self.target_type)
        exact_pairs: dict[EdgeType, tuple[NodeType, NodeType]] = {
            "CONTAINS_ELEMENT": ("Substance", "Element"),
            "REACTANT_IN": ("Substance", "Reaction"),
            "PRODUCT_OF": ("Substance", "Reaction"),
            "HAS_PHENOMENON": ("Reaction", "Phenomenon"),
            "TESTS": ("Question", "Concept"),
            "RELATES_TO": (self.source_type, "Concept"),
        }
        expected = exact_pairs[self.type]
        tests_reaction = self.type == "TESTS" and pair == ("Question", "Reaction")
        contains_element = self.type == "CONTAINS_ELEMENT" and pair in {
            ("Ion", "Element"),
            ("Substance", "Element"),
        }
        species_reaction = self.type in {"REACTANT_IN", "PRODUCT_OF"} and pair in {
            ("Ion", "Reaction"),
            ("Substance", "Reaction"),
        }
        if self.type == "CONTAINS_ELEMENT":
            valid = contains_element
        elif self.type in {"REACTANT_IN", "PRODUCT_OF"}:
            valid = species_reaction
        else:
            valid = pair == expected or tests_reaction
        if not valid:
            raise ValueError(f"{self.type} requires {expected[0]} -> {expected[1]}")
        return self


class ElementKnowledgeGraph(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    center_node_id: UUID = Field(alias="centerNodeId")
    nodes: list[KnowledgeNode]
    edges: list[KnowledgeEdge]
    empty_reason: str | None = Field(default=None, alias="emptyReason")


class ElementWikiSections(BaseModel):
    ions: list[KnowledgeNode]
    substances: list[KnowledgeNode]
    reactions: list[KnowledgeNode]
    phenomena: list[KnowledgeNode]
    concepts: list[KnowledgeNode]
    questions: list[KnowledgeNode]


class ElementWikiPage(BaseModel):
    identity: ElementWikiIdentity
    classification: ElementWikiClassification
    properties: list[ElementWikiProperty]
    sections: ElementWikiSections
    graph: ElementKnowledgeGraph
    sources: list[ElementWikiSource]


@dataclass(frozen=True, slots=True)
class ElementKnowledgeSnapshot:
    species: tuple[CatalogSpeciesResult, ...] = ()
    reactions: tuple[CatalogReactionResult, ...] = ()
    knowledge: tuple[CatalogKnowledgeResult, ...] = ()
    structures: tuple[CatalogStructureEntry, ...] = ()


_GRAPH_NAMESPACE = uuid5(NAMESPACE_URL, "chem-wiki:element-wiki:graph:v1")


def _graph_id(value: str) -> UUID:
    return uuid5(_GRAPH_NAMESPACE, value)


def _source_keys(field_name: str, sources: tuple[PublishedFieldSource, ...]) -> list[str]:
    return sorted({source.source_key for source in sources if source.field_name == field_name})


def _property(
    *,
    key: PropertyKey,
    field_name: str,
    label: str,
    sources: tuple[PublishedFieldSource, ...],
    value: float | None = None,
    lower: float | None = None,
    upper: float | None = None,
    unit: str | None = None,
    qualifier: str | None = None,
    uncertainty: float | None = None,
) -> ElementWikiProperty:
    source_keys = _source_keys(field_name, sources)
    is_available = bool(source_keys) and (value is not None or lower is not None)
    return ElementWikiProperty(
        key=key,
        label=label,
        status="available" if is_available else "missing",
        value=value if is_available else None,
        lower=lower if is_available else None,
        upper=upper if is_available else None,
        unit=unit if is_available else None,
        qualifier=qualifier if is_available else None,
        uncertainty=uncertainty if is_available else None,
        sourceKeys=source_keys if is_available else [],
    )


def _build_sources(sources: tuple[PublishedFieldSource, ...]) -> list[ElementWikiSource]:
    grouped: dict[str, dict[str, object]] = {}
    for source in sources:
        item = grouped.setdefault(
            source.source_key,
            {
                "key": source.source_key,
                "title": source.title,
                "publisher": source.publisher,
                "url": source.url,
                "licenseCode": source.license_code,
                "retrievedAt": source.retrieved_at,
                "fields": set(),
            },
        )
        field_alias = _PROPERTY_ALIASES.get(source.field_name, source.field_name)
        fields = item["fields"]
        assert isinstance(fields, set)
        fields.add(field_alias)
        item["retrievedAt"] = max(item["retrievedAt"], source.retrieved_at)

    result: list[ElementWikiSource] = []
    for key in sorted(grouped):
        item = grouped[key]
        fields = item["fields"]
        assert isinstance(fields, set)
        item["fields"] = sorted(fields)
        result.append(ElementWikiSource.model_validate(item))
    return result


def build_element_wiki(
    element: PeriodicTableElement,
    snapshot: CanonicalElementWikiSnapshot,
    knowledge_snapshot: ElementKnowledgeSnapshot | None = None,
) -> ElementWikiPage:
    related = knowledge_snapshot or ElementKnowledgeSnapshot()
    properties = [
        _property(
            key="atomicWeight",
            field_name="atomic_weight",
            label="相对原子质量",
            sources=snapshot.published_sources,
            value=snapshot.atomic_weight_value,
            lower=snapshot.atomic_weight_lower,
            upper=snapshot.atomic_weight_upper,
            uncertainty=snapshot.atomic_weight_uncertainty,
        ),
        _property(
            key="electronegativity",
            field_name="electronegativity",
            label="电负性",
            sources=snapshot.published_sources,
            value=snapshot.electronegativity_value,
            unit=snapshot.electronegativity_scale,
        ),
        _property(
            key="firstIonizationEnergy",
            field_name="first_ionization_energy",
            label="第一电离能",
            sources=snapshot.published_sources,
            value=snapshot.first_ionization_energy_value,
            unit=snapshot.first_ionization_energy_unit,
        ),
        _property(
            key="atomicRadius",
            field_name="atomic_radius",
            label="原子半径",
            sources=snapshot.published_sources,
            value=snapshot.atomic_radius_value,
            unit=snapshot.atomic_radius_unit,
            qualifier=snapshot.atomic_radius_qualifier,
        ),
    ]
    center = KnowledgeNode(
        id=element.id,
        type="Element",
        label=f"{element.name_zh} {element.symbol}",
        secondaryLabel=f"原子序数 {element.atomic_number}",
        href=f"/elements/{element.id}",
    )
    structures = {entry.application_species_id: entry for entry in related.structures}
    species_nodes: dict[str, KnowledgeNode] = {}
    for species in related.species:
        structure = structures.get(species.application_id)
        charge = f" · 电荷 {species.charge:+d}" if species.charge else ""
        species_nodes[species.consolidated_id] = KnowledgeNode(
            id=species.application_id,
            type="Ion" if species.entity_kind == "ion" else "Substance",
            label=species.name_zh,
            secondaryLabel=f"{species.formula}{charge}",
            href=(
                f"/structure-lab?species={species.application_id}"
                if structure is not None and structure.canonical_smiles
                else None
            ),
            description="可在结构实验室中继续探索"
            if structure and structure.canonical_smiles
            else None,
        )
    reaction_nodes = {
        reaction.consolidated_id: KnowledgeNode(
            id=reaction.application_reaction_id or _graph_id(reaction.consolidated_id),
            type="Reaction",
            label=reaction.name_zh,
            secondaryLabel=reaction.equation,
            href=f"/equation-lab?reaction={reaction.consolidated_id}",
            description="在方程实验室中打开",
        )
        for reaction in related.reactions
    }
    knowledge_nodes = {
        item.consolidated_id: KnowledgeNode(
            id=item.application_id,
            type="Concept" if item.source_type == "concept" else "Phenomenon",
            label=item.display_name_zh,
            secondaryLabel=item.content_zh,
            description=item.content_zh,
        )
        for item in related.knowledge
    }
    edges: list[KnowledgeEdge] = []
    for species_id, node in species_nodes.items():
        edges.append(
            KnowledgeEdge(
                id=_graph_id(f"contains:{species_id}:{element.id}"),
                type="CONTAINS_ELEMENT",
                source=node.id,
                sourceType=node.type,
                target=element.id,
                targetType="Element",
                label="包含该元素",
            )
        )
    for reaction in related.reactions:
        reaction_node = reaction_nodes[reaction.consolidated_id]
        for participant in reaction.participants:
            if participant.species_id not in species_nodes:
                continue
            species_node = species_nodes[participant.species_id]
            edge_type: EdgeType = "REACTANT_IN" if participant.role == "reactant" else "PRODUCT_OF"
            edges.append(
                KnowledgeEdge(
                    id=_graph_id(
                        f"{edge_type}:{participant.species_id}:{reaction.consolidated_id}"
                    ),
                    type=edge_type,
                    source=species_node.id,
                    sourceType=species_node.type,
                    target=reaction_node.id,
                    targetType="Reaction",
                    label="作为反应物" if edge_type == "REACTANT_IN" else "作为生成物",
                )
            )
        for item in related.knowledge:
            if reaction.source_id not in item.related_reaction_ids:
                continue
            knowledge_node = knowledge_nodes[item.consolidated_id]
            edge_type = "RELATES_TO" if item.source_type == "concept" else "HAS_PHENOMENON"
            edges.append(
                KnowledgeEdge(
                    id=_graph_id(f"{edge_type}:{reaction.consolidated_id}:{item.consolidated_id}"),
                    type=edge_type,
                    source=reaction_node.id,
                    sourceType="Reaction",
                    target=knowledge_node.id,
                    targetType=knowledge_node.type,
                    label="相关概念" if edge_type == "RELATES_TO" else "实验现象",
                )
            )
    sections = ElementWikiSections(
        ions=[node for node in species_nodes.values() if node.type == "Ion"],
        substances=[node for node in species_nodes.values() if node.type == "Substance"],
        reactions=list(reaction_nodes.values()),
        phenomena=[node for node in knowledge_nodes.values() if node.type == "Phenomenon"],
        concepts=[node for node in knowledge_nodes.values() if node.type == "Concept"],
        questions=[],
    )
    return ElementWikiPage(
        identity=ElementWikiIdentity(
            id=element.id,
            atomicNumber=element.atomic_number,
            symbol=element.symbol,
            nameZh=element.name_zh,
            nameEn=element.name_en,
            status=element.status,
        ),
        classification=ElementWikiClassification(
            category=element.category,
            period=element.layout.period,
            group=element.layout.group,
            block=element.layout.block,
        ),
        properties=properties,
        sections=sections,
        graph=ElementKnowledgeGraph(
            centerNodeId=element.id,
            nodes=[
                center,
                *species_nodes.values(),
                *reaction_nodes.values(),
                *knowledge_nodes.values(),
            ],
            edges=edges,
            emptyReason=None if edges else "暂无已审核的相关物质、反应或概念数据",
        ),
        sources=_build_sources(snapshot.published_sources),
    )
