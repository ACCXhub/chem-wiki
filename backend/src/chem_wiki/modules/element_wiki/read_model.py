"""M04 Element Wiki and element-centred knowledge graph read model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
        if pair != expected and not tests_reaction:
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
) -> ElementWikiPage:
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
    sections = ElementWikiSections(
        ions=[],
        substances=[],
        reactions=[],
        phenomena=[],
        concepts=[],
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
            nodes=[center],
            edges=[],
            emptyReason="暂无已审核的相关物质、反应或概念数据",
        ),
        sources=_build_sources(snapshot.published_sources),
    )
