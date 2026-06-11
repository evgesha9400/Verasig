"""Shared tolerant JSON-object extraction from LLM-CLI stdout (ADR 0006).

Both the rule distiller and the LLM fallback extractor read free-form model
output (bare or ```json-fenced) the same way: grab the first brace-delimited
object. Returns the raw JSON string, or None when none is present — the caller
decides whether absence is fatal (distiller raises) or a miss (fallback None).
"""

import re

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def find_json_object(stdout: str) -> str | None:
    match = _JSON_OBJECT.search(stdout)
    return match.group(0) if match is not None else None
