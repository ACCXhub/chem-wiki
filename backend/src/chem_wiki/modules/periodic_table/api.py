"""HTTP boundary owned by M03."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, sessionmaker

from chem_wiki.config import Settings
from chem_wiki.infrastructure.database import create_database_engine, create_session_factory

from .postgres import PostgresPeriodicTableReader
from .read_model import PeriodicTableElement


class PeriodicTableReader(Protocol):
    def list_elements(self) -> list[PeriodicTableElement]: ...


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    engine = create_database_engine(Settings().database_url)
    return create_session_factory(engine)


def get_periodic_table_reader() -> Iterator[PeriodicTableReader]:
    with _session_factory()() as session:
        yield PostgresPeriodicTableReader(session)


router = APIRouter(prefix="/v1", tags=["periodic-table"])


@router.get("/elements", response_model=list[PeriodicTableElement])
def list_elements(
    reader: Annotated[PeriodicTableReader, Depends(get_periodic_table_reader)],
) -> list[PeriodicTableElement]:
    return reader.list_elements()
