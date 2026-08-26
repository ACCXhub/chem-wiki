"""Minimal backend query boundary for the consolidated catalog."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Literal, Protocol

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
        limit: int = 20,
    ) -> list[CatalogSpeciesResult]: ...

    def get_reaction(self, consolidated_id: str) -> CatalogReactionResult | None: ...


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    engine = create_database_engine(Settings().database_url)
    return create_session_factory(engine)


def get_catalog_reader() -> Iterator[CatalogReader]:
    with _session_factory()() as session:
        yield PostgresCatalogReader(session)


router = APIRouter(prefix="/v1/catalog", tags=["knowledge-catalog"])


@router.get("/species", response_model=list[CatalogSpeciesResult])
def search_species(
    reader: Annotated[CatalogReader, Depends(get_catalog_reader)],
    q: str = "",
    primary_category: str | None = None,
    equation_mode: Literal["molecular", "ionic", "net_ionic"] | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[CatalogSpeciesResult]:
    return reader.search_species(
        query=q,
        primary_category=primary_category,
        equation_mode=equation_mode,
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
