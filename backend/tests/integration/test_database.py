from importlib import import_module

import pytest
from sqlalchemy import text


@pytest.mark.integration
def test_database_session_executes_query() -> None:
    config = import_module("chem_wiki.config")
    database = import_module("chem_wiki.infrastructure.database")

    settings = config.Settings()
    engine = database.create_database_engine(settings.database_url)

    try:
        session_factory = database.create_session_factory(engine)
        with session_factory() as session:
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
