import base64
import os

import pytest
from fastapi.testclient import TestClient

from verasig.api.app import create_app
from verasig.config import Settings


@pytest.fixture
def app(session_factory, pg_url):
    settings = Settings(
        _env_file=None,
        database_url_override=pg_url,
        jwt_secret="test-secret",
        secret_keys=f"test:{base64.b64encode(os.urandom(32)).decode()}",
    )
    return create_app(settings, session_factory=session_factory)


@pytest.fixture
def client(app):
    return TestClient(app)
