"""Verasig - Template Mining: template normalization.

Turns a message into a structural skeleton by replacing the parts that vary
(instruments, directions, prices, market markers) with placeholders, then
uppercasing the label words the author actually wrote. Two messages with the
same shape but different symbols and numbers collapse to one templateKey, and
so do messages of one format that differ only in how many targets they list.
"""

from __future__ import annotations

from dataclasses import dataclass

import regex as re

from .directions import detect_directions, is_emoji_direction
from .fields import LEVERAGE
from .instruments import detect_instruments
from .intervals import by_start_then_longest_key
from .prices import detect_prices
from .scoring import candidate_text
from .text import normalize_message_text, to_clean_lines

MARKET_MARKER = re.compile(
    r"\b(current market price|current price|cmp|market|now)\b", re.IGNORECASE
)
LIST_GAP = re.compile(r"^[\s/,]*$")


@dataclass
class _Span:
    start: int
    end: int
    token: str


@dataclass
class TemplateResult:
    template_key: str
    normalized_template: str


def _instrument_spans(clean, overlay, instruments) -> list[_Span]:
    entities = (
        instruments if instruments is not None else detect_instruments(clean, overlay)
    )
    return [_Span(e.start, e.end, "<INSTRUMENT>") for e in entities]


def _direction_spans(clean, overlay, directions) -> list[_Span]:
    entities = (
        directions if directions is not None else detect_directions(clean, overlay)
    )
    return [
        _Span(e.start, e.end, "<SIDE_EMOJI>" if is_emoji_direction(e) else "<SIDE>")
        for e in entities
    ]


def _price_spans(clean, prices) -> list[_Span]:
    # Consecutive single levels separated only by list punctuation become one
    # <PRICE_LIST>; a range is always its own <RANGE>; a lone level is a <PRICE>.
    prices = prices if prices is not None else detect_prices(clean)
    spans: list[_Span] = []
    group: list = []

    def flush() -> None:
        nonlocal group
        if not group:
            return
        token = "<PRICE_LIST>" if len(group) >= 2 else "<PRICE>"
        spans.append(_Span(group[0].start, group[-1].end, token))
        group = []

    for price in prices:
        if price.type == "range":
            flush()
            spans.append(_Span(price.start, price.end, "<RANGE>"))
            continue
        previous = group[-1] if group else None
        joinable = previous is not None and bool(
            LIST_GAP.match(clean[previous.end : price.start])
        )
        if previous is not None and not joinable:
            flush()
        group.append(price)
    flush()
    return spans


def _market_spans(clean: str) -> list[_Span]:
    return [
        _Span(m.start(), m.start() + len(m.group(0)), "MARKET")
        for m in MARKET_MARKER.finditer(clean)
    ]


def _collect_spans(clean: str, overlay: dict | None, detections: dict) -> list[_Span]:
    instruments = detections.get("instruments")
    directions = detections.get("directions")
    prices = detections.get("prices")
    spans = [
        *_instrument_spans(clean, overlay, instruments),
        *_direction_spans(clean, overlay, directions),
        *_price_spans(clean, prices),
        *_market_spans(clean),
    ]
    spans.sort(key=by_start_then_longest_key(lambda s: (s.start, s.end)))

    accepted: list[_Span] = []
    cursor = -1
    for span in spans:
        if span.start < cursor:
            continue  # drop overlap
        accepted.append(span)
        cursor = span.end
    return accepted


def _apply_spans(clean: str, spans: list[_Span]) -> str:
    result = ""
    cursor = 0
    for span in spans:
        result += clean[cursor : span.start] + span.token
        cursor = span.end
    return result + clean[cursor:]


def _tidy_lines(text: str) -> str:
    return "\n".join(to_clean_lines(text))


# [0-9] not \d: \d would also match non-ASCII digits.
_BARE_ORDINAL = re.compile(r"\bTP[0-9]+\b")
_ORDINAL_KEEP = re.compile(r"^:?\s*<PRICE")


def _collapse_bare_ordinals(template: str) -> str:
    # A numbered TP that owns a value keeps its ordinal ("TP1: <PRICE>"); a bare
    # reference collapses to TP<N> so "hit TP1"/"hit TP2" updates group together.
    def repl(match: re.Match) -> str:
        after = template[match.end() :]
        return match.group(0) if _ORDINAL_KEEP.match(after) else "TP<N>"

    return _BARE_ORDINAL.sub(repl, template)


def _collapse_leverage(template: str) -> str:
    # Leverage ("20X", Cyrillic "20Х", ranges "5-10X") varies per signal but is
    # not structural; collapse it before decoration stripping splits "5-10X".
    return LEVERAGE.sub("<LEVERAGE>", template)


# Decoration that varies per message and must not split a format family.
DECORATIVE_EMOJI = re.compile(r"[\p{Extended_Pictographic}️⃣‍]")
NON_STRUCTURAL = re.compile(r"[^\p{L}\p{N}\s<>_@\n]")
SIDE_EMOJI_RUN = re.compile(r"(?:<SIDE_EMOJI>\s*)+")
PRICE_RUN = re.compile(r"<PRICE>(?:\s+<PRICE>)+")

# The structural vocabulary: the label words that actually shape a signal.
STRUCT_WORDS = {
    # English
    "BUY",
    "SELL",
    "LONG",
    "SHORT",
    "CALL",
    "PUT",
    "ENTRY",
    "ENTER",
    "ENTRIES",
    "ZONE",
    "LIMIT",
    "ORDER",
    "MARKET",
    "NOW",
    "CMP",
    "CURRENT",
    "PRICE",
    "STOP",
    "STOPLOSS",
    "SL",
    "INVALIDATION",
    "INVALID",
    "BELOW",
    "ABOVE",
    "TP",
    "TAKE",
    "PROFIT",
    "PROFITS",
    "TARGET",
    "TARGETS",
    "TGT",
    "PARTIAL",
    "HIT",
    "RANGE",
    "LEVERAGE",
    # Russian
    "МОНЕТА",
    "МОНЕТУ",
    "МОНЕТЕ",
    "ПОКУПКА",
    "ПРОДАЖА",
    "КУПИЛ",
    "ПРОДАЛ",
    "ЛОНГ",
    "ШОРТ",
    "ПЛЕЧО",
    "ВХОД",
    "СТОП",
    "ЦЕЛИ",
    "ЦЕЛЬ",
    "ЦЕЛЕЙ",
    "ТЕЙК",
    "ТЕЙКИ",
    "ФИКСИРУЕМ",
    "ПРИБЫЛЬ",
    "ПРИБЫЛИ",
    "НА",
    "ПО",
    "РЫНКУ",
    "В",
}
# A line must carry at least one of these value placeholders to be a field line.
VALUE_PLACEHOLDER = re.compile(
    r"<(?:INSTRUMENT|PRICE|PRICE_LIST|RANGE|SIDE|SIDE_EMOJI|LEVERAGE|N)>"
)
TOKEN = re.compile(r"<[A-Z_]+>|[\p{L}][\p{L}\p{N}]*")
_TP_NUM = re.compile(r"^TP\d*$")


def _strip_decoration(template: str) -> str:
    return NON_STRUCTURAL.sub(" ", DECORATIVE_EMOJI.sub("", template))


def _collapse_price_runs(template: str) -> str:
    return "\n".join(
        PRICE_RUN.sub("<PRICE_LIST>", line) for line in template.split("\n")
    )


BARE_PRICE_LINE = re.compile(r"^(?:[0-9]+\s+)?<PRICE>$")
# One target per line ("TP <PRICE>", "TP2 <PRICE>", "TARGET <PRICE>").
TARGET_PRICE_LINE = re.compile(r"^(?:TP[0-9]*|TARGET)\s*<PRICE>$")


def _collapse_runs(
    template: str, pattern: re.Pattern, single: str | None, many: str
) -> str:
    """Replace each run of consecutive ``pattern`` lines: a lone line becomes
    ``single`` (kept verbatim when None), two or more become one ``many`` line."""
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if len(run) == 1:
            out.append(run[0] if single is None else single)
        elif run:
            out.append(many)
        run.clear()

    for line in template.split("\n"):
        if pattern.match(line):
            run.append(line)
            continue
        flush()
        out.append(line)
    flush()
    return "\n".join(out)


def _collapse_target_lines(template: str) -> str:
    # A run of bare price lines is one target list; so is a run of 2+ one-target
    # lines, so a 2-TP and a 3-TP message of one format share a template.
    template = _collapse_runs(template, BARE_PRICE_LINE, "<PRICE>", "<PRICE_LIST>")
    return _collapse_runs(template, TARGET_PRICE_LINE, None, "TP <PRICE_LIST>")


PRICE_OR_RANGE = re.compile(r"<(?:PRICE|RANGE)>")
TARGET_LIST_LABEL = re.compile(r"\b(?:TAKE PROFITS|TARGETS|PARTIAL)\b")
TARGET_LIST_LABEL_RU = [
    "ЦЕЛИ",
    "ЦЕЛЬ",
    "ЦЕЛЕЙ",
    "ТЕЙК",
    "ТЕЙКИ",
    "ФИКСИРУЕМ ПРИБЫЛЬ НА",
]
INDEPENDENT_ENTRY_LABEL = re.compile(r"\b(?:ENTRY|ENTRIES|ENTER|ZONE)\b|@")
_TRAILING_PRICE = re.compile(r"<PRICE>$")
_LIMIT_ORDER = re.compile(r"(^|\s)LIMIT ORDER\b")
_MULTI_SPACE = re.compile(r"\s+")


def _line_has_target_list_label(line: str) -> bool:
    return bool(TARGET_LIST_LABEL.search(line)) or any(
        label in line for label in TARGET_LIST_LABEL_RU
    )


def _line_has_independent_priced_entry(line: str) -> bool:
    if not PRICE_OR_RANGE.search(line):
        return False
    return bool(INDEPENDENT_ENTRY_LABEL.search(line)) or "ВХОД" in line


def _canonicalize_target_price_arity(line: str) -> str:
    if not _line_has_target_list_label(line):
        return line
    return _TRAILING_PRICE.sub("<PRICE_LIST>", line)


def _canonicalize_limit_order_modifier(
    line: str, has_independent_priced_entry: bool
) -> str:
    if not has_independent_priced_entry or PRICE_OR_RANGE.search(line):
        return line
    replaced = _LIMIT_ORDER.sub(r"\1", line)
    return _MULTI_SPACE.sub(" ", replaced).strip()


def _canonicalize_template_family(template: str) -> str:
    lines = template.split("\n")
    has_independent_priced_entry = any(
        _line_has_independent_priced_entry(line) for line in lines
    )
    result = []
    for line in lines:
        line = _canonicalize_limit_order_modifier(line, has_independent_priced_entry)
        line = _canonicalize_target_price_arity(line)
        result.append(line)
    return "\n".join(result)


# A real field line is known labels + placeholders with at most ONE stray word.
MAX_STRAY_WORDS = 1
_STRAY_RUN = re.compile(r"(?:<\*>\s*)+")


def _wildcard_line(line: str) -> tuple[str, int]:
    stray = 0

    def repl(match: re.Match) -> str:
        nonlocal stray
        token = match.group(0)
        if token.startswith("<"):
            return token
        upper = token.upper()
        if upper in STRUCT_WORDS or _TP_NUM.match(upper):
            return upper
        stray += 1
        return "<*>"

    mapped = TOKEN.sub(repl, line)
    compact = _MULTI_SPACE.sub(" ", _STRAY_RUN.sub("<*> ", mapped)).strip()
    return compact, stray


def _keep_structural_lines(template: str) -> str:
    kept = []
    for line in template.split("\n"):
        compact, stray = _wildcard_line(line)
        if stray <= MAX_STRAY_WORDS and VALUE_PLACEHOLDER.search(compact):
            kept.append(compact)
    return "\n".join(kept)


def _utf16_code_units(text: str):
    """JS `charCodeAt` iterates UTF-16 code units; an astral char is two
    surrogates. Mirror that so the hash matches JS for any input, not just BMP."""
    for ch in text:
        code = ord(ch)
        if code > 0xFFFF:
            code -= 0x10000
            yield 0xD800 + (code >> 10)
            yield 0xDC00 + (code & 0x3FF)
        else:
            yield code


def hash_string(text: str) -> str:
    h = 0
    for unit in _utf16_code_units(text):
        h = (h * 31 + unit) & 0xFFFFFFFF
    if h == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    n = h
    while n:
        out = digits[n % 36] + out
        n //= 36
    return out


def normalize_template(
    candidate: dict,
    overlay: dict | None = None,
    detections: dict | None = None,
) -> TemplateResult:
    detections = detections or {}
    normalized = detections.get("normalized") or normalize_message_text(
        candidate_text(candidate)
    )
    clean = normalized.clean
    spans = _collect_spans(clean, overlay, detections)
    replaced = SIDE_EMOJI_RUN.sub(
        "<SIDE_EMOJI> ",
        _strip_decoration(_collapse_leverage(_apply_spans(clean, spans).upper())),
    )
    skeleton = _collapse_bare_ordinals(_collapse_price_runs(_tidy_lines(replaced)))
    skeleton = _keep_structural_lines(_collapse_target_lines(skeleton))
    skeleton = _canonicalize_template_family(skeleton)
    return TemplateResult(
        template_key=f"tpl_{hash_string(skeleton)}", normalized_template=skeleton
    )
