import os
import subprocess
from collections.abc import Callable, Mapping


class ClaudeCodeRunnerError(RuntimeError):
    """Raised when the Claude Code subprocess cannot complete a prompt."""


def make_claude_code_runner(
    oauth_token: str,
    model: str,
    command: str = "claude",
    timeout_seconds: int = 180,
) -> Callable[[str], str]:
    token = oauth_token.strip()
    if not token:
        raise ClaudeCodeRunnerError("VERASIG_CLAUDE_CODE_OAUTH_TOKEN must not be blank")

    def run(prompt: str) -> str:
        try:
            completed = subprocess.run(
                [
                    command,
                    "--print",
                    "--output-format",
                    "text",
                    "--no-session-persistence",
                    "--safe-mode",
                    "--tools",
                    "",
                    "--model",
                    model,
                ],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=_claude_code_environment(os.environ, token),
            )
        except subprocess.TimeoutExpired as error:
            raise ClaudeCodeRunnerError("Claude Code runner timed out") from error
        if completed.returncode != 0:
            raise ClaudeCodeRunnerError(_failure_message(completed))
        return completed.stdout.strip()

    return run


def _claude_code_environment(
    base_environment: Mapping[str, str], oauth_token: str
) -> dict[str, str]:
    environment = dict(base_environment)
    environment.pop("ANTHROPIC_API_KEY", None)
    environment["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
    return environment


def _failure_message(completed: subprocess.CompletedProcess[str]) -> str:
    detail = completed.stderr.strip() or completed.stdout.strip()
    if detail:
        return f"Claude Code runner failed: {detail}"
    return f"Claude Code runner failed with exit code {completed.returncode}"
