from fastapi import FastAPI

from chem_wiki.api.health import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(title="chem-wiki")
    application.include_router(health_router)
    return application


app = create_app()
