from collections.abc import Sequence

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from verasig.api.errors import ApiError, api_error_handler
from verasig.api.routers import (
    auth,
    chats,
    distill,
    exchanges,
    health,
    labels,
    risk,
    telegram,
    user,
    verify,
)
from verasig.config import Settings
from verasig.foundation import telegram_session
from verasig.foundation.anthropic_runner import make_anthropic_runner
from verasig.foundation.bybit_account import verify_api_keys
from verasig.foundation.db import make_session_factory
from verasig.foundation.security import SecretCipher
from verasig.services.distillation.rule_distiller import AnthropicDistiller
from verasig.services.jobs.registry import JobRegistry

ALL_ROUTERS: Sequence[APIRouter] = (
    health.router,
    auth.router,
    user.router,
    telegram.router,
    exchanges.router,
    chats.router,
    labels.router,
    distill.router,
    verify.router,
    risk.router,
)


def create_app(
    settings: Settings, session_factory: sessionmaker | None = None
) -> FastAPI:
    app = FastAPI(title="Verasig API")
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session_factory(
        settings.database_url
    )
    app.state.jobs = JobRegistry()
    app.state.secret_cipher = SecretCipher.from_spec(settings.secret_keys)
    app.state.telegram_auth = telegram_session
    app.state.exchange_verifier = verify_api_keys
    app.state.distiller_factory = lambda: AnthropicDistiller(
        runner=make_anthropic_runner(
            settings.anthropic_api_key, settings.anthropic_model
        )
    )
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
