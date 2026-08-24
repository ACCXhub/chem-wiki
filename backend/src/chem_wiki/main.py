from fastapi import FastAPI

from chem_wiki.api.health import router as health_router
from chem_wiki.modules.periodic_table.api import router as periodic_table_router


def create_app() -> FastAPI:
    application = FastAPI(title="chem-wiki")
    application.include_router(health_router)
    application.include_router(periodic_table_router)
    return application


app = create_app()
