import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import LabelKind
from verasig.domain.parser_rule import ParserRule
from verasig.features.rules.repository import (
    read_distillation_examples,
    read_labels,
    upsert_filter_rule,
    upsert_parser_rules,
)
from verasig.features.rules.rule_distiller import FilterDistillationError
from verasig.features.rules.schemas import JobOut
from verasig.features.rules.views import present_rules
from verasig.foundation.http.auth_dependencies import require_feed
from verasig.foundation.http.errors import ApiError
from verasig.foundation.http.sse import sse_stream
from verasig.foundation.jobs.registry import JobAlreadyRunningError, JobTerminalError

router = APIRouter(prefix="/feeds/{external_id}")

DISTILL_STAGES = (
    ("labels_read", "Reading labels"),
    ("filter_distilling", "Distilling filter rules"),
    ("filter_validating", "Validating against labelled messages"),
    ("parser_distilling", "Distilling parser rules"),
    ("rules_persisting", "Saving ruleset"),
    ("rules_complete", "Ruleset compiled"),
)
DISTILL_TOTAL_STEPS = len(DISTILL_STAGES)
DISTILL_STAGE_BY_KEY = {
    stage: {"phase": phase, "step": index}
    for index, (stage, phase) in enumerate(DISTILL_STAGES, start=1)
}


def _job_key(user_id: UUID, channel_id: int) -> str:
    return f"{user_id}:{channel_id}:distill"


def _signal_label_count(session, user_id: UUID, channel_id: int) -> int:
    return sum(
        1
        for label in read_labels(session, channel_id, user_id)
        if label.label is LabelKind.SIGNAL
    )


def _label_counts(examples) -> tuple[int, int]:
    signal_count = sum(1 for example in examples if example.label == LabelKind.SIGNAL)
    return signal_count, len(examples) - signal_count


def _progress_payload(
    stage: str,
    counts: tuple[int, int],
    attempt: int | None = None,
) -> dict:
    definition = DISTILL_STAGE_BY_KEY[stage]
    signal_count, noise_count = counts
    payload = {
        "stage": stage,
        "phase": definition["phase"],
        "step": definition["step"],
        "totalSteps": DISTILL_TOTAL_STEPS,
        "signalLabels": signal_count,
        "noiseLabels": noise_count,
    }
    if attempt is not None:
        payload["attempt"] = attempt
    return payload


def _publish_progress(
    publisher,
    stage: str,
    counts: tuple[int, int],
    attempt: int | None = None,
) -> None:
    publisher.progress(_progress_payload(stage, counts, attempt))


def _scope_filter_rule(rule: FilterRule, user_id: UUID, channel_id: int) -> FilterRule:
    return rule.model_copy(
        update={
            "user_id": user_id,
            "channel_id": channel_id,
            "rule_id": f"{user_id}:{channel_id}-filter-v{rule.version}",
        }
    )


def _scope_parser_rules(
    rules: list[ParserRule], user_id: UUID, channel_id: int
) -> list[ParserRule]:
    return [
        rule.model_copy(
            update={
                "user_id": user_id,
                "channel_id": channel_id,
                "rule_id": f"{user_id}:{channel_id}-parser-{index + 1}-v{rule.version}",
            }
        )
        for index, rule in enumerate(rules)
    ]


async def _run_distill(
    publisher,
    user_id: UUID,
    channel_id: int,
    session_factory,
    distiller_factory,
) -> dict:
    with session_factory() as session:
        examples = read_distillation_examples(session, channel_id, user_id)
    counts = _label_counts(examples)
    _publish_progress(publisher, "labels_read", counts)
    distiller = distiller_factory()
    _publish_progress(publisher, "filter_distilling", counts)
    try:
        filter_rule = _scope_filter_rule(
            await asyncio.to_thread(distiller.distill_filter, examples),
            user_id,
            channel_id,
        )
    except FilterDistillationError as error:
        raise JobTerminalError(str(error), {"validation": error.report}) from error
    _publish_progress(publisher, "filter_validating", counts)
    _publish_progress(publisher, "parser_distilling", counts)
    parser_rules = _scope_parser_rules(
        await asyncio.to_thread(distiller.distill_parsers, examples),
        user_id,
        channel_id,
    )
    _publish_progress(publisher, "rules_persisting", counts)
    with session_factory() as session:
        upsert_filter_rule(session, filter_rule)
        upsert_parser_rules(session, parser_rules)
        session.commit()
    _publish_progress(publisher, "rules_complete", counts)
    return {"rules": len(filter_rule.include_patterns)}


@router.post("/distill", status_code=status.HTTP_202_ACCEPTED)
async def start_distill(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> JobOut:
    with request.app.state.session_factory() as session:
        if _signal_label_count(session, subscription.user_id, int(external_id)) < 5:
            raise ApiError(409, "LABELS_INSUFFICIENT", "Need at least 5 signal labels")
    key = _job_key(subscription.user_id, int(external_id))
    try:
        request.app.state.jobs.start(
            key,
            lambda publisher: _run_distill(
                publisher,
                subscription.user_id,
                int(external_id),
                request.app.state.session_factory,
                request.app.state.distiller_factory,
            ),
        )
    except JobAlreadyRunningError as error:
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Job is already running") from error
    return JobOut(job_id=key)


@router.get("/distill/progress")
def distill_progress(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
):
    key = _job_key(subscription.user_id, int(external_id))
    if not request.app.state.jobs.has_job(key):
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found")
    return sse_stream(request.app.state.jobs, key)


@router.get("/rules")
def rules(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> dict:
    with request.app.state.session_factory() as session:
        return {"rules": present_rules(session, subscription.user_id, int(external_id))}
