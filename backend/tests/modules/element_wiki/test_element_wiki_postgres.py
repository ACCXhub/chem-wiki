from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.dialects import postgresql

from chem_wiki.modules.periodic_table.read_model import (
    CanonicalElementSnapshot,
    build_periodic_table,
)


class PeriodicReaderStub:
    def __init__(self, element_id: UUID) -> None:
        self._elements = build_periodic_table(
            [
                CanonicalElementSnapshot(
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
        )

    def list_elements(self):
        return self._elements


class ResultStub:
    def __init__(self, *, one=None, rows=None) -> None:
        self._one = one
        self._rows = rows or []

    def one_or_none(self):
        return self._one

    def all(self):
        return self._rows


class SessionStub:
    def __init__(self, results: list[ResultStub]) -> None:
        self._results = iter(results)
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return next(self._results)


def test_postgres_reader_projects_only_published_values_and_safe_source_metadata() -> None:
    from chem_wiki.modules.element_wiki.postgres import PostgresElementWikiReader

    element_id = UUID("12345678-1234-5678-1234-567812345678")
    property_row = SimpleNamespace(
        atomic_weight_value=None,
        atomic_weight_lower=None,
        atomic_weight_upper=None,
        atomic_weight_uncertainty=None,
        electronegativity_value=3.16,
        electronegativity_scale="Pauling",
        first_ionization_energy_value=12.968,
        first_ionization_energy_unit="eV",
        atomic_radius_value=79.0,
        atomic_radius_unit="pm",
        atomic_radius_qualifier="covalent",
    )
    published_rows = [
        SimpleNamespace(
            field_name="electronegativity",
            source_key="pubchem",
            title="PubChem",
            publisher="National Library of Medicine",
            source_url="https://pubchem.ncbi.nlm.nih.gov/element/Chlorine",
            base_url="https://pubchem.ncbi.nlm.nih.gov",
            license_code="public-domain",
            retrieved_at=datetime(2026, 8, 24, tzinfo=UTC),
        ),
        SimpleNamespace(
            field_name="first_ionization_energy",
            source_key="nist-asd",
            title="NIST Atomic Spectra Database",
            publisher="NIST",
            source_url=None,
            base_url="https://physics.nist.gov/asd",
            license_code=None,
            retrieved_at=datetime(2026, 8, 24, tzinfo=UTC),
        ),
    ]
    session = SessionStub([ResultStub(one=property_row), ResultStub(rows=published_rows)])

    page = PostgresElementWikiReader(
        session,  # type: ignore[arg-type]
        PeriodicReaderStub(element_id),  # type: ignore[arg-type]
    ).get_element(element_id)

    assert page is not None
    properties = {item.key: item for item in page.properties}
    assert properties["electronegativity"].value == 3.16
    assert properties["atomicRadius"].status == "missing"
    assert [source.key for source in page.sources] == ["nist-asd", "pubchem"]
    assert page.sources[0].url == "https://physics.nist.gov/asd"

    sql = "\n".join(
        str(statement.compile(dialect=postgresql.dialect())) for statement in session.statements
    )
    assert "element_published_value" in sql
    assert "element_source" in sql
    assert "raw_payload" not in sql
    assert "raw_value" not in sql
    assert "selection_reason" not in sql


def test_postgres_reader_returns_none_for_unknown_stable_uuid_without_querying_m02_details() -> (
    None
):
    from chem_wiki.modules.element_wiki.postgres import PostgresElementWikiReader

    known_id = UUID(int=17)
    session = SessionStub([])

    page = PostgresElementWikiReader(
        session,  # type: ignore[arg-type]
        PeriodicReaderStub(known_id),  # type: ignore[arg-type]
    ).get_element(UUID(int=99))

    assert page is None
    assert session.statements == []
