"""Minimal backend query boundary for the consolidated catalog."""

import json
import re
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Literal, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker

from chem_wiki.config import Settings
from chem_wiki.infrastructure.database import create_database_engine, create_session_factory

from .postgres import PostgresCatalogReader
from .read_model import CatalogReactionResult, CatalogSpeciesResult


class CatalogReader(Protocol):
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
    ) -> list[CatalogSpeciesResult]: ...

    def get_reaction(self, consolidated_id: str) -> CatalogReactionResult | None: ...

    def find_reactions_by_application_ids(
        self, application_ids: list[UUID]
    ) -> list[CatalogReactionResult]: ...


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    engine = create_database_engine(Settings().database_url)
    return create_session_factory(engine)


def get_catalog_reader() -> Iterator[CatalogReader]:
    with _session_factory()() as session:
        yield PostgresCatalogReader(session)


router = APIRouter(prefix="/v1/catalog", tags=["knowledge-catalog"])

_ELEMENT_SYMBOL = re.compile(r"[A-Z][a-z]?")


def _parse_composition(value: str | None) -> dict[str, int] | None:
    if value is None:
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=422, detail="composition 必须是元素计数 JSON object"
        ) from error
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=422, detail="composition 必须包含至少一个元素")
    if any(
        not isinstance(element, str)
        or _ELEMENT_SYMBOL.fullmatch(element) is None
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count <= 0
        for element, count in payload.items()
    ):
        raise HTTPException(status_code=422, detail="composition 必须使用正整数元素计数")
    return dict(sorted(payload.items()))


@router.get("/species", response_model=list[CatalogSpeciesResult])
def search_species(
    reader: Annotated[CatalogReader, Depends(get_catalog_reader)],
    q: str = "",
    primary_category: str | None = None,
    equation_mode: Literal["molecular", "ionic", "net_ionic"] | None = None,
    composition: str | None = None,
    charge: int | None = None,
    entity_kind: Literal["ion", "substance"] | None = None,
    application_id: Annotated[list[UUID] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[CatalogSpeciesResult]:
    if application_id is not None and len(application_id) > 50:
        raise HTTPException(status_code=422, detail="application_id 最多可查询 50 个")
    return reader.search_species(
        query=q,
        primary_category=primary_category,
        equation_mode=equation_mode,
        composition=_parse_composition(composition),
        total_charge=charge,
        entity_kind=entity_kind,
        application_ids=application_id,
        limit=limit,
    )


@router.get("/reactions/{consolidated_id}", response_model=CatalogReactionResult)
def get_reaction(
    consolidated_id: str,
    reader: Annotated[CatalogReader, Depends(get_catalog_reader)],
) -> CatalogReactionResult:
    reaction = reader.get_reaction(consolidated_id)
    if reaction is None:
        raise HTTPException(status_code=404, detail="未找到 catalog Reaction")
    return reaction
