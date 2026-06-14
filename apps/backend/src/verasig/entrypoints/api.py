from collections.abc import Sequence

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from verasig.config import Settings
from verasig.features.accounts import auth_routes, user_routes
from verasig.features.exchanges import routes as exchange_routes
from verasig.features.risk import routes as risk_routes
from verasig.features.rules import (
    distill_routes,
    label_routes,
    verify_routes,
)
from verasig.features.rules.rule_distiller import AnthropicDistiller
from verasig.features.signals import routes as signal_routes
from verasig.features.simulation import routes as simulation_routes
from verasig.features.sources import routes as source_routes
from verasig.features.sources.backfill_job_coordinator import BackfillJobCoordinator
from verasig.features.telegram_links import routes as telegram_link_routes
from verasig.foundation.database.session import make_session_factory
from verasig.foundation.http import health_routes
from verasig.foundation.http.access_logging import (
    install_health_check_access_log_filter,
)
from verasig.foundation.http.errors import ApiError, api_error_handler
from verasig.foundation.jobs.registry import JobRegistry
from verasig.foundation.llm.anthropic_runner import make_anthropic_runner
from verasig.foundation.market_data.bybit_account import verify_api_keys
from verasig.foundation.market_data.bybit_market_data import BybitKlineClient
from verasig.foundation.security.secrets import SecretCipher
from verasig.foundation.telegram import session as telegram_session

ALL_ROUTERS: Sequence[APIRouter] = (
    health_routes.router,
    auth_routes.router,
    user_routes.router,
    telegram_link_routes.router,
    exchange_routes.router,
    source_routes.router,
    simulation_routes.router,
    label_routes.router,
    distill_routes.router,
    verify_routes.router,
    risk_routes.router,
    signal_routes.router,
)


def create_app(
    settings: Settings, session_factory: sessionmaker | None = None
) -> FastAPI:
    install_health_check_access_log_filter()
    app = FastAPI(title="Verasig API")
    app.state.settings = settings
    app.state.jwt_secret = settings.jwt_secret_spec()
    app.state.session_factory = session_factory or make_session_factory(
        settings.database_url
    )
    app.state.jobs = JobRegistry()
    app.state.backfill_jobs = BackfillJobCoordinator(
        app.state.session_factory,
        app.state.jobs,
        settings.backfill_batch_size,
    )
    app.state.backfill_jobs.mark_interrupted_runs_failed()
    app.state.secret_cipher = SecretCipher.from_spec(settings.secret_key_spec())
    app.state.telegram_auth = telegram_session
    app.state.exchange_verifier = verify_api_keys
    app.state.market_data_factory = BybitKlineClient
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


def create_app_from_env() -> FastAPI:
    return create_app(Settings())
