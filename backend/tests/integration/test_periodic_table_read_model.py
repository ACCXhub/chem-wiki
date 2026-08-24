from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.infrastructure.database import create_database_engine
from chem_wiki.modules.element_data import (
    PubChemAdapter,
    bootstrap_element_identities,
    import_pubchem_elements,
)
from chem_wiki.modules.periodic_table import PostgresPeriodicTableReader

pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).parents[2]


def test_postgres_reader_projects_published_properties_without_source_schema() -> None:
    payload = {
        "Table": {
            "Columns": {
                "Column": [
                    "AtomicNumber",
                    "Symbol",
                    "Name",
                    "Electronegativity",
                    "AtomicRadius",
                    "IonizationEnergy",
                ]
            },
            "Row": [
                {
                    "Cell": ["1", "H", "Hydrogen", "2.2", "120", "13.598"],
                }
            ],
        }
    }
    adapter = PubChemAdapter(
        fetch_json=lambda _url, _timeout: payload,
        clock=lambda: datetime(2026, 8, 24, tzinfo=UTC),
    )
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    engine = create_database_engine(Settings().database_url)

    try:
        with Session(engine) as session:
            bootstrap_element_identities(session)
            import_pubchem_elements(session, adapter=adapter, atomic_numbers={1})
            session.flush()

            elements = PostgresPeriodicTableReader(session).list_elements()

            assert len(elements) == 118
            assert elements[0].symbol == "H"
            assert elements[0].properties.electronegativity.model_dump() == {
                "value": 2.2,
                "unit": "Pauling",
            }
            assert elements[0].properties.first_ionization_energy.model_dump() == {
                "value": 13.598,
                "unit": "eV",
            }
            assert elements[1].properties.electronegativity.value is None
            assert "source" not in elements[0].model_dump_json()
            assert "claim" not in elements[0].model_dump_json()
            session.rollback()
    finally:
        engine.dispose()
        command.downgrade(alembic_config, "base")
