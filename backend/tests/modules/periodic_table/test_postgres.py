from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.dialects import postgresql

from chem_wiki.modules.periodic_table import PostgresPeriodicTableReader


class ResultStub:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class SessionStub:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return ResultStub(self._rows)


def _row(atomic_number: int) -> SimpleNamespace:
    published = atomic_number == 1
    return SimpleNamespace(
        id=UUID(int=atomic_number),
        atomic_number=atomic_number,
        symbol="H" if atomic_number == 1 else f"E{atomic_number}",
        name_zh="氢" if atomic_number == 1 else f"元素{atomic_number}",
        name_en="hydrogen" if atomic_number == 1 else f"element-{atomic_number}",
        electronegativity_value=2.2,
        electronegativity_scale="Pauling",
        first_ionization_energy_value=13.598,
        first_ionization_energy_unit="eV",
        electronegativity_publication_id=UUID(int=1) if published else None,
        ionization_publication_id=UUID(int=2) if published else None,
    )


def test_postgres_reader_returns_only_published_canonical_properties() -> None:
    session = SessionStub([_row(number) for number in range(1, 119)])

    elements = PostgresPeriodicTableReader(session).list_elements()  # type: ignore[arg-type]

    assert len(elements) == 118
    assert elements[0].properties.electronegativity.value == 2.2
    assert elements[0].properties.first_ionization_energy.value == 13.598
    assert elements[1].properties.electronegativity.value is None
    assert elements[1].properties.first_ionization_energy.value is None

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "element_property" in sql
    assert "element_published_value" in sql
    assert "element_source_record" not in sql
    assert "element_claim" not in sql
