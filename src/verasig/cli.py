import asyncio

import typer
from sqlalchemy import text

from verasig.config import Settings
from verasig.foundation.db import make_engine, make_session_factory
from verasig.foundation.telegram_session import (
    CredentialsMissingError,
    SessionMissingError,
    fetch_account,
    format_account,
    make_client,
    run_login,
    save_session_string,
)
from verasig.foundation.telegram_source import TelethonSource
from verasig.services.ingestion.backfill import backfill as run_backfill
from verasig.storage import repositories as repo

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


@app.command()
def backfill(reference: str) -> None:
    """Capture a channel's history into RawTelegramMessage (resumable, chunked)."""
    settings = Settings()
    try:
        client = make_client(settings)
    except (CredentialsMissingError, SessionMissingError) as error:
        raise _fail(error) from error
    session_factory = make_session_factory(settings.database_url)
    result = asyncio.run(
        _connected_backfill(client, reference, session_factory, settings)
    )
    typer.echo(
        f"backfill complete: channel {result.channel_id} · +{result.inserted} new "
        f"· cursor={result.captured_through_message_id}"
    )


async def _connected_backfill(client, reference, session_factory, settings):
    async with client:
        source = TelethonSource(client)
        return await run_backfill(
            source, reference, session_factory, settings.backfill_batch_size
        )


@app.command()
def stats(reference: str) -> None:
    """Print capture count + cursor for an already-backfilled channel."""
    settings = Settings()
    session_factory = make_session_factory(settings.database_url)
    with session_factory() as session:
        channel = repo.find_channel(session, reference)
        if channel is None:
            raise _fail(ValueError(f"no channel matching {reference!r}; run backfill"))
        typer.echo(
            format_stats(channel, repo.count_messages(session, channel.channel_id))
        )


def format_stats(channel, message_count: int) -> str:
    parts = [channel.title]
    if channel.handle:
        parts.append(f"@{channel.handle}")
    parts.append(f"id={channel.channel_id}")
    parts.append(f"captured={message_count}")
    cursor = channel.captured_through_message_id
    parts.append(f"cursor={cursor if cursor is not None else 'none'}")
    if channel.subscriber_count is not None:
        parts.append(f"subs={channel.subscriber_count}")
    return " · ".join(parts)


if __name__ == "__main__":
    app()
