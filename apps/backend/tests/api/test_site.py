import base64
import os

import pytest
from fastapi.testclient import TestClient

from verasig.config import Settings, SettingsError
from verasig.entrypoints.site import create_site

INDEX_HTML = '<!doctype html><div id="root"></div>'


@pytest.fixture
def web_dist(tmp_path):
    (tmp_path / "index.html").write_text(INDEX_HTML)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    return tmp_path


def _settings(pg_url, web_dist_dir):
    return Settings(
        _env_file=None,
        database_url_override=pg_url,
        jwt_secret="s" * 32,
        secret_keys=f"test:{base64.b64encode(os.urandom(32)).decode()}",
        web_dist_dir=web_dist_dir,
    )


@pytest.fixture
def site_client(session_factory, pg_url, web_dist):
    site = create_site(_settings(pg_url, web_dist), session_factory=session_factory)
    with TestClient(site) as client:
        yield client


def test_api_is_served_under_api_prefix(site_client):
    assert site_client.get("/api/health").status_code == 200


def test_static_asset_is_served(site_client):
    response = site_client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == "console.log('app')"


@pytest.mark.parametrize("path", ["/", "/app", "/app/feeds/x"])
def test_deep_link_returns_index(site_client, path):
    response = site_client.get(path)
    assert response.status_code == 200
    assert '<div id="root">' in response.text


def test_unknown_api_path_is_not_index(site_client):
    response = site_client.get("/api/no-such-route")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert '<div id="root">' not in response.text


def test_site_requires_web_dist_dir(pg_url):
    with pytest.raises(SettingsError, match="VERASIG_WEB_DIST_DIR"):
        create_site(_settings(pg_url, None))


def test_site_requires_index_html(pg_url, tmp_path):
    with pytest.raises(SettingsError, match="index.html"):
        create_site(_settings(pg_url, tmp_path))
