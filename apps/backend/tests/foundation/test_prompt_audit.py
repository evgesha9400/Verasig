import json

from verasig.domain.label import DistillationExample, LabelKind
from verasig.foundation.llm.prompt_audit import (
    make_distill_prompt_auditor,
    make_distill_response_auditor,
    make_distill_skip_auditor,
    make_distill_validation_auditor,
)


def _examples() -> list[DistillationExample]:
    return [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text="BTC long entry",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.NOISE,
            text="Market commentary",
        ),
    ]


def test_distill_prompt_audit_writes_attempt_validation_and_skip_artifacts(tmp_path):
    examples = _examples()
    make_distill_prompt_auditor(tmp_path)("filter-attempt-1", "prompt text", examples)
    make_distill_response_auditor(tmp_path)(
        "filter-attempt-1", "response text", examples
    )
    make_distill_validation_auditor(tmp_path)(
        "filter-attempt-1",
        {
            "include_patterns": ["long"],
            "total_labelled_examples": 2,
            "signal_count": 1,
            "noise_count": 1,
            "modifier_count": 0,
            "accuracy": 100.0,
            "false_positive_message_ids": [],
            "false_negative_message_ids": [],
        },
        examples,
    )
    make_distill_skip_auditor(tmp_path)(
        "parser", "parser distillation skipped because signal_count=0", examples
    )

    names = sorted(path.name for path in tmp_path.iterdir())
    assert any(name.endswith("filter-attempt-1.prompt.txt") for name in names)
    assert any(name.endswith("filter-attempt-1.response.txt") for name in names)
    validation_path = next(
        path
        for path in tmp_path.iterdir()
        if path.name.endswith("filter-attempt-1.validation.json")
    )
    assert any(name.endswith("parser.skipped.txt") for name in names)

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert validation["include_patterns"] == ["long"]
    assert validation["accuracy"] == 100.0
    assert validation["label_count"] == 2
