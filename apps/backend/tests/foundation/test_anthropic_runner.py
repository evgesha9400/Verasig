from types import SimpleNamespace

import verasig.foundation.llm.anthropic_runner as module
from verasig.foundation.llm.anthropic_runner import make_anthropic_runner


def test_anthropic_runner_concatenates_text_blocks_and_passes_model(monkeypatch):
    calls = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(type="text", text="hello "),
                    SimpleNamespace(type="tool_use", text="ignored"),
                    SimpleNamespace(type="text", text="world"),
                ]
            )

    class FakeAnthropic:
        def __init__(self, api_key):
            self.api_key = api_key
            self.messages = FakeMessages()

    monkeypatch.setattr(module.anthropic, "Anthropic", FakeAnthropic)

    run = make_anthropic_runner("api-key", "claude-sonnet-4-6")

    assert run("prompt") == "hello world"
    assert calls == [
        {
            "model": "claude-sonnet-4-6",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": "prompt"}],
        }
    ]
