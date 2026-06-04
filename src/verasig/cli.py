import asyncio
import os
import subprocess
from pathlib import Path

import typer
from sqlalchemy import text

from verasig.config import Settings
from verasig.foundation.db import make_engine, make_session_factory
from verasig.foundation.exchange import StaticExchange
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
from verasig.services.extraction.extract_service import ExtractService
from verasig.services.ingestion.backfill import backfill as run_backfill
from verasig.services.ingestion.candidate_derivation import (
    derive_candidates,
    sweep_advisory,
)
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
def migrate() -> None:
    """Apply database migrations (alembic upgrade head)."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")
    typer.echo("migrations applied")


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


def _resolve_channel_id(session_factory, reference: str) -> int:
    with session_factory() as session:
        channel = repo.find_channel(session, reference)
    if channel is None:
        raise _fail(ValueError(f"no channel matching {reference!r}; run backfill"))
    return channel.channel_id


@app.command()
def candidates(reference: str) -> None:
    """Derive advisory RawSignalEvents from stored messages (seed + FilterRules)."""
    session_factory = make_session_factory(Settings().database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    created = derive_candidates(session_factory, channel_id, StaticExchange())
    typer.echo(f"candidates derived: channel {channel_id} · +{created} new")


@app.command()
def extract(reference: str) -> None:
    """Apply ParserRules to candidates → ExtractedSignal | UnrecognizedSignal."""
    session_factory = make_session_factory(Settings().database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    signals, unrecognized = _extract_candidates(session_factory, channel_id)
    typer.echo(
        f"extracted: channel {channel_id} · {signals} signals "
        f"· {unrecognized} unrecognized"
    )


def _extract_candidates(session_factory, channel_id: int) -> tuple[int, int]:
    with session_factory() as session:
        service = ExtractService(repo.read_parser_rules(session, channel_id))
        events = repo.read_signal_events(session, channel_id)
    signals, unrecognized = [], []
    for event in events:
        outcome = service.extract(event)
        if outcome.signal is not None:
            signals.append(outcome.signal)
        else:
            unrecognized.append(outcome.unrecognized)
    with session_factory() as session:
        repo.insert_extracted_signals(session, signals)
        repo.insert_unrecognized_signals(session, unrecognized)
        session.commit()
    return len(signals), len(unrecognized)


@app.command()
def sweep(reference: str) -> None:
    """Advisory parser sweep over all messages → PARSER_BACKFILL + drift."""
    session_factory = make_session_factory(Settings().database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    with session_factory() as session:
        parser_rules = repo.read_parser_rules(session, channel_id)
    recovered, drift = sweep_advisory(session_factory, channel_id, parser_rules)
    typer.echo(f"sweep: channel {channel_id} · +{recovered} recovered · +{drift} drift")


@app.command()
def workbench(reference: str) -> None:
    """Launch the Streamlit distillation workbench (real-LLM Distil gated)."""
    session_factory = make_session_factory(Settings().database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    _launch_workbench(channel_id)


def _launch_workbench(channel_id: int) -> None:
    app_path = Path(__file__).parent / "ui" / "app.py"
    environment = {**os.environ, "VERASIG_WORKBENCH_CHANNEL": str(channel_id)}
    subprocess.run(["streamlit", "run", str(app_path)], env=environment, check=False)


if __name__ == "__main__":
    app()
