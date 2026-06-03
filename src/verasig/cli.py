import asyncio

import typer
from sqlalchemy import text

from verasig.config import Settings
from verasig.foundation.db import make_engine
from verasig.foundation.telegram_session import (
    CredentialsMissingError,
    SessionMissingError,
    fetch_account,
    format_account,
    make_client,
    run_login,
    save_session_string,
)

app = typer.Typer(help="Verasig — local observer CLI.")


@app.callback()
def main() -> None:
    """Verasig — local observer CLI (one subcommand per pipeline stage)."""


def _fail(error: Exception) -> typer.Exit:
    typer.echo(str(error), err=True)
    return typer.Exit(1)


@app.command()
def health() -> None:
    """Verify the app can connect to the configured Postgres database."""
    with make_engine(Settings().database_url).connect() as connection:
        connection.execute(text("select 1"))
    typer.echo("OK: db connected")


@app.command()
def login() -> None:
    """Authenticate the Telegram account once (interactive); persist the session."""
    settings = Settings()
    try:
        session_string = asyncio.run(run_login(settings))
    except CredentialsMissingError as error:
        raise _fail(error) from error
    save_session_string(settings.session_path, session_string)
    typer.echo("login complete; session saved")


@app.command()
def whoami() -> None:
    """Print the logged-in Telegram account (non-interactive)."""
    settings = Settings()
    try:
        client = make_client(settings)
    except (CredentialsMissingError, SessionMissingError) as error:
        raise _fail(error) from error
    typer.echo(format_account(asyncio.run(fetch_account(client))))


if __name__ == "__main__":
    app()
