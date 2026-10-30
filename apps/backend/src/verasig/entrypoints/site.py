"""One process for the deployed site: the API under /api, the built web app at /."""

from pathlib import Path, PurePosixPath

from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from verasig.config import Settings, SettingsError
from verasig.entrypoints.api import create_app


class SinglePageFiles(StaticFiles):
    """Static files that answer unknown client routes with index.html.

    A missing file path (one with an extension, such as an asset from an older
    deploy) stays a 404, so the browser does not get HTML for a script.
    """

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or PurePosixPath(path).suffix:
                raise
            return await super().get_response("index.html", scope)


def create_site(
    settings: Settings, session_factory: sessionmaker | None = None
) -> Starlette:
    web_dist_dir = _require_web_dist_dir(settings.web_dist_dir)
    api = create_app(settings, session_factory=session_factory)
    return Starlette(
        routes=[
            Mount("/api", app=api),
            Mount("/", app=SinglePageFiles(directory=web_dist_dir, html=True)),
        ]
    )


def create_site_from_env() -> Starlette:
    return create_site(Settings())


def _require_web_dist_dir(web_dist_dir: Path | None) -> Path:
    if web_dist_dir is None:
        raise SettingsError("VERASIG_WEB_DIST_DIR must point at the built web app")
    if not (web_dist_dir / "index.html").is_file():
        raise SettingsError(f"VERASIG_WEB_DIST_DIR has no index.html: {web_dist_dir}")
    return web_dist_dir
