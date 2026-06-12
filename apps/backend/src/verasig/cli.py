import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import typer
from sqlalchemy import text

from verasig.config import Settings
from verasig.domain.deletion import DeletedSignalEvidence, DeletionConfidence
from verasig.domain.event import RawSignalEvent
from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.message import RawTelegramMessage
from verasig.domain.protocols import LlmExtractor, MarketData
from verasig.domain.score import (
    ProviderScore,
    ProviderScoreExplanation,
    ScoreComponent,
)
from verasig.domain.signal import ExtractedSignal, ExtractionMethod, SignalEventType
from verasig.domain.simulation import SimOutcome
from verasig.foundation.bybit_market_data import BybitKlineClient
from verasig.foundation.db import make_engine, make_session_factory
from verasig.foundation.static_exchange import StaticExchange
from verasig.foundation.telegram_session import (
    CredentialsMissingError,
    SessionMissingError,
    fetch_account,
    format_account,
    make_client,
    run_login,
    save_session_string,
)
from verasig.foundation.telethon_source import (
    ChannelReferenceResolutionError,
    TelethonSource,
)
from verasig.services.deletion.rescan import RescanAborted
from verasig.services.deletion.rescan import rescan as run_rescan
from verasig.services.extraction.extract_service import ExtractOutcome, ExtractService
from verasig.services.extraction.llm_fallback import ClaudeCliExtractor
from verasig.services.ingestion.backfill import backfill as run_backfill
from verasig.services.ingestion.candidate_derivation import (
    derive_candidates,
    sweep_advisory,
)
from verasig.services.ingestion.live import LiveIngestionResult
from verasig.services.ingestion.live import ingest_live as run_live
from verasig.services.lifecycle.fold import fold
from verasig.services.scoring.scorecard import build_provider_score
from verasig.services.scoring.simulator import simulate_outcomes_from_market_data
from verasig.storage import repositories as repo

app = typer.Typer(help="Verasig CLI.")


@app.callback()
def main() -> None:
    """Verasig CLI."""


def _fail(error: Exception) -> typer.Exit:
    typer.echo(str(error), err=True)
    return typer.Exit(1)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


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
    try:
        result = asyncio.run(
            _connected_backfill(client, reference, session_factory, settings)
        )
    except ChannelReferenceResolutionError as error:
        raise _fail(error) from error
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


def _make_live_source(client) -> TelethonSource:
    return TelethonSource(client)


@app.command()
def live(channels: list[str]) -> None:
    """Run queue-first live capture for one or more Telegram channels."""
    settings = Settings()
    try:
        client = make_client(settings)
    except (CredentialsMissingError, SessionMissingError) as error:
        raise _fail(error) from error
    session_factory = make_session_factory(settings.database_url)
    try:
        result = asyncio.run(_connected_live(client, channels, session_factory))
    except ChannelReferenceResolutionError as error:
        raise _fail(error) from error
    typer.echo(format_live_result(result))


async def _connected_live(client, references: list[str], session_factory):
    async with client:
        source = _make_live_source(client)
        channel_ids = await _register_live_channels(source, references, session_factory)
        return await run_live(source, channel_ids, session_factory)


async def _register_live_channels(source, references: list[str], session_factory):
    channels = [await source.resolve_channel(reference) for reference in references]
    with session_factory() as session:
        for channel in channels:
            repo.upsert_channel(session, channel)
        session.commit()
    return [channel.channel_id for channel in channels]


def _format_latency(result: LiveIngestionResult) -> str:
    if result.median_latency is None:
        return "n/a"
    return f"{result.median_latency.total_seconds():.1f}s"


def format_live_result(result: LiveIngestionResult) -> str:
    channel_ids = ",".join(str(channel_id) for channel_id in result.channel_ids)
    return (
        f"live: channels={channel_ids} · +{result.inserted} captured "
        f"· duplicates={result.duplicates} · deleted={result.deleted} "
        f"· median_latency={_format_latency(result)}"
    )


def _find_known_channel(session, reference: str | int):
    try:
        return repo.find_channel(session, reference)
    except ChannelReferenceResolutionError as error:
        raise _fail(error) from error


@app.command()
def stats(reference: str) -> None:
    """Print capture count + cursor for an already-backfilled channel."""
    settings = Settings()
    session_factory = make_session_factory(settings.database_url)
    with session_factory() as session:
        channel = _find_known_channel(session, reference)
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


def _num(value) -> str:
    return f"{value}"


def _format_take_profits(values: list) -> str:
    return f"[{', '.join(_num(value) for value in values)}]"


def _format_levels(step: FoldStep) -> str:
    parts = []
    if step.effective_stop_loss is not None:
        parts.append(f"sl={_num(step.effective_stop_loss)}")
    if step.effective_take_profits:
        parts.append(f"tps={_format_take_profits(step.effective_take_profits)}")
    parts.append(f"size={_num(step.effective_size)}")
    if step.effective_entry is not None:
        parts.append(f"entry={_num(step.effective_entry)}")
    return " ".join(parts)


def _format_leg_note(step: FoldStep) -> str:
    if step.leg_size is None or step.leg_size == 0:
        return ""
    if step.leg_size > 0:
        return "  (add)"
    return "  (reduce)" if step.event_type is SignalEventType.MODIFY else ""


def _format_step(step: FoldStep) -> str:
    when = step.at.strftime("%H:%M")
    kind = step.event_type.value
    return f"  {when} {kind:<9} {_format_levels(step)}{_format_leg_note(step)}"


def _format_header(folded: FoldedSignal) -> str:
    closed = folded.closed_at.strftime("%Y-%m-%dT%H:%MZ") if folded.closed_at else "-"
    return (
        f"{folded.symbol} {folded.side.value}  root={folded.root_signal_id.hex[:8]}  "
        f"steps={len(folded.timeline)}  closed={closed}"
    )


def format_folded(folded: FoldedSignal) -> str:
    rows = [_format_step(step) for step in folded.timeline]
    return "\n".join([_format_header(folded), *rows])


def _deletion_header(channel) -> str:
    parts = [channel.title]
    if channel.handle:
        parts.append(f"@{channel.handle}")
    parts.append(f"id={channel.channel_id}")
    return " · ".join(parts)


def _is_signal_deletion(item: DeletedSignalEvidence) -> bool:
    return item.confidence is DeletionConfidence.CONFIRMED and item.was_signal_candidate


def _format_deleted_signal(item: DeletedSignalEvidence) -> str:
    when = item.first_seen_at.strftime("%Y-%m-%dT%H:%MZ") if item.first_seen_at else "-"
    return f'  #{item.message_id} {when} "{item.original_text or ""}"'


def _count_suspected(evidence: list[DeletedSignalEvidence]) -> int:
    return sum(
        1 for item in evidence if item.confidence is DeletionConfidence.SUSPECTED
    )


def format_deletions(channel, evidence: list[DeletedSignalEvidence]) -> str:
    """Header + signal-confirmed deletions (chatter hidden) + suspected-gap count."""
    signals = sorted(
        (item for item in evidence if _is_signal_deletion(item)),
        key=lambda item: item.message_id,
    )
    rows = [_format_deleted_signal(item) for item in signals]
    footer = f"SUSPECTED gaps: {_count_suspected(evidence)}"
    return "\n".join([_deletion_header(channel), *rows, footer])


def _score_header(channel, score: ProviderScore) -> str:
    parts = [f"ProviderScore {channel.title}"]
    if channel.handle:
        parts.append(f"@{channel.handle}")
    parts.append(f"id={channel.channel_id}")
    parts.append(f"score={score.score:.4f}")
    parts.append(f"weights={score.weights_version}")
    parts.append(f"signals={score.signal_count}")
    parts.append(f"simulated={score.simulated_count}")
    return " ".join(parts)


def _format_component(component: ScoreComponent) -> str:
    return (
        f"  {component.name} raw={component.raw_value:.4f} "
        f"normalized={component.normalized:.4f} weight={component.weight:.4f} "
        f"contribution={component.contribution:.4f}"
    )


def format_score(channel, score: ProviderScore) -> str:
    rows = [_format_component(component) for component in score.components]
    return "\n".join([_score_header(channel, score), "Components:", *rows])


def format_explanation(explanation: ProviderScoreExplanation) -> str:
    rows = [f"  {note}" for note in explanation.notes]
    return "\n".join(["Notes:", *rows])


def _resolve_channel_id(session_factory, reference: str) -> int:
    with session_factory() as session:
        channel = _find_known_channel(session, reference)
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
def lifecycle(reference: str) -> None:
    """Fold a channel's lifecycles and print each timeline (offline, read-only)."""
    session_factory = make_session_factory(Settings().database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    for folded in _fold_channel(session_factory, channel_id):
        typer.echo(format_folded(folded))


def _fold_channel(session_factory, channel_id: int) -> list[FoldedSignal]:
    with session_factory() as session:
        signals = repo.read_extracted_signals(session, channel_id)
        events = repo.read_signal_events(session, channel_id)
        messages = repo.read_messages(session, channel_id)
    return fold(signals, events, messages)


def _make_market_data() -> MarketData:
    return BybitKlineClient()


def _parse_until(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_simulation_until(until: datetime | None) -> datetime:
    if until is None:
        raise _fail(ValueError("pass --until <iso-datetime> when using --simulate"))
    return until


def _simulate_channel(
    messages: list[RawTelegramMessage],
    events: list[RawSignalEvent],
    signals: list[ExtractedSignal],
    market_data: MarketData,
    until: datetime,
) -> list[SimOutcome]:
    folded_signals = fold(signals, events, messages)
    return simulate_outcomes_from_market_data(
        folded_signals=folded_signals,
        market_data=market_data,
        end=until,
    )


def _score_channel(
    session_factory,
    channel_id: int,
    *,
    market_data: MarketData | None = None,
    simulation_until: datetime | None = None,
) -> tuple[object, ProviderScore, ProviderScoreExplanation]:
    with session_factory() as session:
        channel = repo.find_channel(session, channel_id)
        messages = repo.read_messages(session, channel_id)
        events = repo.read_signal_events(session, channel_id)
        signals = repo.read_extracted_signals(session, channel_id)
        unrecognized = repo.read_unrecognized_signals(session, channel_id)
        deletion_evidence = repo.read_deletion_evidence(session, channel_id)
        message_count = repo.count_messages(session, channel_id)
    sim_outcomes = (
        []
        if market_data is None or simulation_until is None
        else _simulate_channel(messages, events, signals, market_data, simulation_until)
    )
    score, explanation = build_provider_score(
        channel=channel,
        messages=messages,
        message_count=message_count,
        events=events,
        signals=signals,
        unrecognized=unrecognized,
        deletions=deletion_evidence,
        sim_outcomes=sim_outcomes,
        computed_at=_utc_now(),
    )
    return channel, score, explanation


@app.command("score")
def score_provider(
    reference: str,
    simulate: bool = typer.Option(False, "--simulate"),
    until: str | None = typer.Option(None, "--until"),
) -> None:
    """Print the recomputed ProviderScore + explanation (offline, read-only)."""
    session_factory = make_session_factory(Settings().database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    parsed_until = _parse_until(until)
    market_data = _make_market_data() if simulate else None
    simulation_until = _require_simulation_until(parsed_until) if simulate else None
    channel, score, explanation = _score_channel(
        session_factory,
        channel_id,
        market_data=market_data,
        simulation_until=simulation_until,
    )
    typer.echo(format_score(channel, score))
    typer.echo(format_explanation(explanation))


@app.command()
def rescan(reference: str) -> None:
    """Re-fetch live ids, diff vs stored, persist DeletedSignalEvidence (gated)."""
    settings = Settings()
    try:
        client = make_client(settings)
    except (CredentialsMissingError, SessionMissingError) as error:
        raise _fail(error) from error
    session_factory = make_session_factory(settings.database_url)
    try:
        result = asyncio.run(_connected_rescan(client, reference, session_factory))
    except (RescanAborted, ValueError) as error:
        raise _fail(error) from error
    typer.echo(
        f"rescan {reference}: {result.confirmed} confirmed "
        f"· {result.suspected} suspected · +{result.written} new"
    )


async def _connected_rescan(client, reference, session_factory):
    async with client:
        return await run_rescan(TelethonSource(client), reference, session_factory)


@app.command()
def deletions(reference: str) -> None:
    """Print stored deletion evidence: signal-confirmed text + suspected-gap count."""
    session_factory = make_session_factory(Settings().database_url)
    with session_factory() as session:
        channel = _find_known_channel(session, reference)
        if channel is None:
            raise _fail(ValueError(f"no channel matching {reference!r}; run backfill"))
        evidence = repo.read_deletion_evidence(session, channel.channel_id)
    typer.echo(format_deletions(channel, evidence))


@dataclass
class _ExtractTally:
    deterministic: int = 0
    llm: int = 0
    unrecognized: int = 0
    drift: int = 0


@app.command()
def extract(
    reference: str,
    no_llm: bool = typer.Option(
        False, "--no-llm", help="disable the LLM fallback (offline, deterministic only)"
    ),
) -> None:
    """Apply ParserRules (+ optional LLM fallback) → ExtractedSignal | Unrecognized."""
    settings = Settings()
    session_factory = make_session_factory(settings.database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    fallback = _resolve_fallback(settings, no_llm)
    tally = _extract_candidates(session_factory, channel_id, fallback)
    typer.echo(
        f"extracted: channel {channel_id} · {tally.deterministic} det "
        f"· {tally.llm} llm · {tally.unrecognized} unrecognized "
        f"· +{tally.drift} parser-drift"
    )


def _make_fallback_extractor(settings: Settings) -> LlmExtractor:
    return ClaudeCliExtractor(command=settings.extractor_command)


def _resolve_fallback(settings: Settings, no_llm: bool) -> LlmExtractor | None:
    if no_llm or not settings.extractor_fallback_enabled:
        return None
    return _make_fallback_extractor(settings)


def _tally_outcome(tally: _ExtractTally, outcome: ExtractOutcome) -> None:
    if outcome.signal is None:
        tally.unrecognized += 1
    elif outcome.signal.extraction_method is ExtractionMethod.LLM_FALLBACK:
        tally.llm += 1
    else:
        tally.deterministic += 1
    tally.drift += len(outcome.drift_warnings)


def _extract_candidates(
    session_factory, channel_id: int, fallback: LlmExtractor | None
) -> _ExtractTally:
    with session_factory() as session:
        rules = repo.read_parser_rules(session, channel_id)
        events = repo.read_signal_events(session, channel_id)
    service = ExtractService(rules, fallback=fallback)
    tally = _ExtractTally()
    with session_factory() as session:
        for event in events:
            outcome = service.extract(event)
            repo.record_outcome(session, outcome)
            _tally_outcome(tally, outcome)
        session.commit()
    return tally


@app.command()
def sweep(reference: str) -> None:
    """Advisory parser sweep over all messages → PARSER_BACKFILL + drift."""
    session_factory = make_session_factory(Settings().database_url)
    channel_id = _resolve_channel_id(session_factory, reference)
    with session_factory() as session:
        parser_rules = repo.read_parser_rules(session, channel_id)
    recovered, drift = sweep_advisory(session_factory, channel_id, parser_rules)
    typer.echo(f"sweep: channel {channel_id} · +{recovered} recovered · +{drift} drift")


if __name__ == "__main__":
    app()
