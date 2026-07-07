"""Verasig - Template Mining: pattern subsumption.

Does an accepted rule's pattern match a message skeleton, allowing it to be
MORE general than the message? Matching is one-directional (pattern ⊇ message)
and structural: same lines, same token count per line, each pattern token
matching its message token.

Faithful port of ``subsumption.js``.
"""

from __future__ import annotations

from .skeleton_tokens import TOKEN

# A general placeholder (key) matches the more-specific placeholders it covers.
# One-directional: <PRICE_LIST> covers <PRICE>, but not the reverse. <RANGE> is
# kept distinct from <PRICE> - a zone entry is not a single level.
SUBSUMES: dict[str, set[str]] = {
    "<PRICE_LIST>": {"<PRICE>"},
    "<SIDE>": {"<SIDE_EMOJI>"},
}


def _tokenize(line: str) -> list[str]:
    return TOKEN.findall(line)


def _token_subsumes(pattern_token: str, message_token: str) -> bool:
    if pattern_token == "<*>":
        return True
    if pattern_token == message_token:
        return True
    return message_token in SUBSUMES.get(pattern_token, set())


def _line_subsumes(pattern_line: str, message_line: str) -> bool:
    pattern_tokens = _tokenize(pattern_line)
    message_tokens = _tokenize(message_line)
    if len(pattern_tokens) != len(message_tokens):
        return False
    return all(
        _token_subsumes(token, message_tokens[index])
        for index, token in enumerate(pattern_tokens)
    )


def pattern_subsumes(pattern: str | None, message: str | None) -> bool:
    """True when the pattern matches (covers) the message skeleton."""
    pattern_lines = (pattern or "").split("\n")
    message_lines = (message or "").split("\n")
    if len(pattern_lines) != len(message_lines):
        return False
    return all(
        _line_subsumes(line, message_lines[index])
        for index, line in enumerate(pattern_lines)
    )
