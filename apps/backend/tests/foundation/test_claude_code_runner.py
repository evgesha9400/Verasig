import subprocess

import pytest

import verasig.foundation.llm.claude_code_runner as module
from verasig.foundation.llm.claude_code_runner import (
    ClaudeCodeRunnerError,
    make_claude_code_runner,
)


def test_claude_code_runner_launches_cli_with_oauth_environment(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, "hello world\n", "")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "stale-api-key")
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    run = make_claude_code_runner(
        " oauth-token ", "sonnet", command="claude-test", timeout_seconds=12
    )

    assert run("prompt") == "hello world"
    assert calls == [
        (
            [
                "claude-test",
                "--print",
                "--output-format",
                "text",
                "--no-session-persistence",
                "--safe-mode",
                "--tools",
                "",
                "--model",
                "sonnet",
            ],
            {
                "input": "prompt",
                "capture_output": True,
                "text": True,
                "timeout": 12,
                "check": False,
                "env": calls[0][1]["env"],
            },
        )
    ]
    assert calls[0][1]["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "oauth-token"
    assert "ANTHROPIC_API_KEY" not in calls[0][1]["env"]


def test_claude_code_runner_rejects_blank_oauth_token():
    with pytest.raises(
        ClaudeCodeRunnerError, match="VERASIG_CLAUDE_CODE_OAUTH_TOKEN must not be blank"
    ):
        make_claude_code_runner(" ", "sonnet")


def test_claude_code_runner_reports_timeout_seconds(monkeypatch):
    def fake_run(args, **_kwargs):
        raise subprocess.TimeoutExpired(args, 12)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    run = make_claude_code_runner(
        "oauth-token", "sonnet", command="claude-test", timeout_seconds=12
    )

    with pytest.raises(
        ClaudeCodeRunnerError, match="Claude Code runner timed out after 12 seconds"
    ):
        run("prompt")
