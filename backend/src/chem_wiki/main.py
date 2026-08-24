from fastapi import FastAPI

from chem_wiki.api.health import router as health_router
from chem_wiki.modules.element_wiki.api import router as element_wiki_router
from chem_wiki.modules.periodic_table.api import router as periodic_table_router
from chem_wiki.modules.reaction_core.api import router as reaction_core_router


def create_app() -> FastAPI:
    application = FastAPI(title="chem-wiki")
    application.include_router(health_router)
    application.include_router(periodic_table_router)
    application.include_router(element_wiki_router)
    application.include_router(reaction_core_router)
    return application


app = create_app()
