from collections.abc import Callable

import anthropic


def make_anthropic_runner(api_key: str, model: str) -> Callable[[str], str]:
    client = anthropic.Anthropic(api_key=api_key)

    def run(prompt: str) -> str:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if block.type == "text")

    return run
