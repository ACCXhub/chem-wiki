"""HTTP boundary owned by M04 Element Wiki."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from chem_wiki.config import Settings
from chem_wiki.infrastructure.database import create_database_engine, create_session_factory
from chem_wiki.modules.periodic_table import PostgresPeriodicTableReader

from .postgres import PostgresElementWikiReader
from .read_model import ElementWikiPage


class ElementWikiReader(Protocol):
    def get_element(self, element_id: UUID) -> ElementWikiPage | None: ...


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    engine = create_database_engine(Settings().database_url)
    return create_session_factory(engine)


def get_element_wiki_reader() -> Iterator[ElementWikiReader]:
    with _session_factory()() as session:
        yield PostgresElementWikiReader(session, PostgresPeriodicTableReader(session))


router = APIRouter(prefix="/v1/elements", tags=["element-wiki"])


@router.get("/{element_id}", response_model=ElementWikiPage)
def get_element_wiki(
    element_id: UUID,
    reader: Annotated[ElementWikiReader, Depends(get_element_wiki_reader)],
) -> ElementWikiPage:
    page = reader.get_element(element_id)
    if page is None:
        raise HTTPException(status_code=404, detail="未找到该元素")
    return page
