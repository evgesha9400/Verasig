import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from verasig.domain.label import DistillationExample, LabelKind


def make_distill_prompt_auditor(
    directory: str | Path = "distill-prompt-audit",
) -> Callable[[str, str, list[DistillationExample]], None]:
    audit_directory = Path(directory)

    def audit(
        prompt_kind: str, prompt: str, examples: list[DistillationExample]
    ) -> None:
        _write_text_artifact(audit_directory, prompt_kind, "prompt", prompt, examples)

    return audit


def make_distill_response_auditor(
    directory: str | Path = "distill-prompt-audit",
) -> Callable[[str, str, list[DistillationExample]], None]:
    audit_directory = Path(directory)

    def audit(
        prompt_kind: str, response: str, examples: list[DistillationExample]
    ) -> None:
        _write_text_artifact(
            audit_directory, prompt_kind, "response", response, examples
        )

    return audit


def make_distill_validation_auditor(
    directory: str | Path = "distill-prompt-audit",
) -> Callable[[str, dict, list[DistillationExample]], None]:
    audit_directory = Path(directory)

    def audit(
        prompt_kind: str, report: dict, examples: list[DistillationExample]
    ) -> None:
        audit_directory.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now(tz=UTC)
        path = audit_directory / _audit_file_name(
            created_at, prompt_kind, "validation", examples, "json"
        )
        path.write_text(
            json.dumps(
                {
                    **_audit_metadata(created_at, prompt_kind, "validation", examples),
                    **report,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    return audit


def make_distill_skip_auditor(
    directory: str | Path = "distill-prompt-audit",
) -> Callable[[str, str, list[DistillationExample]], None]:
    audit_directory = Path(directory)

    def audit(
        prompt_kind: str, reason: str, examples: list[DistillationExample]
    ) -> None:
        _write_text_artifact(audit_directory, prompt_kind, "skipped", reason, examples)

    return audit


def _write_text_artifact(
    audit_directory: Path,
    prompt_kind: str,
    artifact_kind: str,
    content: str,
    examples: list[DistillationExample],
) -> None:
    audit_directory.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(tz=UTC)
    path = audit_directory / _audit_file_name(
        created_at, prompt_kind, artifact_kind, examples, "txt"
    )
    path.write_text(
        _audit_text(created_at, prompt_kind, artifact_kind, content, examples),
        encoding="utf-8",
    )


def _audit_file_name(
    created_at: datetime,
    prompt_kind: str,
    artifact_kind: str,
    examples: list[DistillationExample],
    extension: str,
) -> str:
    first = examples[0]
    timestamp = created_at.strftime("%Y%m%dT%H%M%S%fZ")
    return (
        f"{timestamp}-{first.user_id}-{first.channel_id}-"
        f"{prompt_kind}.{artifact_kind}.{extension}"
    )


def _audit_text(
    created_at: datetime,
    prompt_kind: str,
    artifact_kind: str,
    content: str,
    examples: list[DistillationExample],
) -> str:
    return "\n".join(
        [
            f"{key}={value}"
            for key, value in _audit_metadata(
                created_at, prompt_kind, artifact_kind, examples
            ).items()
        ]
        + [
            "",
            f"--- {artifact_kind} ---",
            content,
            "",
        ]
    )


def _audit_metadata(
    created_at: datetime,
    prompt_kind: str,
    artifact_kind: str,
    examples: list[DistillationExample],
) -> dict:
    first = examples[0]
    return {
        "created_at": created_at.isoformat(),
        "prompt_kind": prompt_kind,
        "artifact_kind": artifact_kind,
        "user_id": str(first.user_id) if first.user_id is not None else None,
        "channel_id": first.channel_id,
        "label_count": len(examples),
        "signal_count": _count(examples, LabelKind.SIGNAL),
        "noise_count": _count(examples, LabelKind.NOISE),
        "modifier_count": _count(examples, LabelKind.MODIFIER),
        "expected_count": sum(
            1 for example in examples if example.expected is not None
        ),
    }


def _count(examples: list[DistillationExample], label: LabelKind) -> int:
    return sum(1 for example in examples if example.label == label)
