from collections.abc import Sequence

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from verasig.api.errors import ApiError, api_error_handler
from verasig.api.routers import health
from verasig.config import Settings
from verasig.foundation.db import make_session_factory
from verasig.services.jobs.registry import JobRegistry

ALL_ROUTERS: Sequence[APIRouter] = (health.router,)


def create_app(
    settings: Settings, session_factory: sessionmaker | None = None
) -> FastAPI:
    app = FastAPI(title="Verasig API")
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session_factory(
        settings.database_url
    )
    app.state.jobs = JobRegistry()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(ApiError, api_error_handler)
    for router in ALL_ROUTERS:
        app.include_router(router)
    return app
