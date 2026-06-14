import base64
import os

import pytest
from fastapi.testclient import TestClient

from verasig.config import Settings
from verasig.entrypoints.api import create_app


@pytest.fixture
def app(session_factory, pg_url):
    settings = Settings(
        _env_file=None,
        database_url_override=pg_url,
        jwt_secret="s" * 32,
        secret_keys=f"test:{base64.b64encode(os.urandom(32)).decode()}",
    )
    return create_app(settings, session_factory=session_factory)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
