from alembic import context

from chem_wiki.config import Settings
from chem_wiki.infrastructure.database import create_database_engine
from chem_wiki.modules.element_data import ElementDataBase
from chem_wiki.modules.knowledge_catalog import KnowledgeCatalogBase
from chem_wiki.modules.reaction_core import ReactionCoreBase

target_metadata = [
    ElementDataBase.metadata,
    ReactionCoreBase.metadata,
    KnowledgeCatalogBase.metadata,
]


def run_migrations_offline() -> None:
    context.configure(
        url=Settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_database_engine(Settings().database_url)

    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
