"""Canonical Telegram channel reference grammar.

The same operator input is used in two places: resolving a live Telegram entity
and looking up an already-captured channel in Postgres. Keeping the grammar here
prevents live and offline commands from accepting different references.
"""

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

_TELEGRAM_HOSTS = frozenset({"t.me", "telegram.me", "telegram.dog"})
_TITLE_PREFIXES = ("title:", "dialog:", "name:")
_USERNAME_PATTERN = re.compile(r"^@?[A-Za-z0-9_]{5,32}$")


class ChannelReferenceResolutionError(ValueError):
    """A Telegram channel reference could not resolve to one channel."""


class ChannelReferenceKind(str, Enum):
    HANDLE = "handle"
    LINK = "link"
    ID = "id"
    TITLE = "title"


@dataclass(frozen=True)
class ChannelReference:
    kind: ChannelReferenceKind
    value: str | int


def parse_channel_reference(reference: str | int) -> ChannelReference:
    if isinstance(reference, int):
        return ChannelReference(ChannelReferenceKind.ID, reference)

    text = str(reference).strip()
    if not text:
        raise ChannelReferenceResolutionError("Telegram channel reference is empty")
    if _is_numeric_reference(text):
        return ChannelReference(ChannelReferenceKind.ID, int(text))
    if _is_title_reference(text):
        return ChannelReference(ChannelReferenceKind.TITLE, _strip_title_prefix(text))
    if _is_telegram_link(text):
        return ChannelReference(ChannelReferenceKind.LINK, text)
    if _is_username_reference(text):
        return ChannelReference(ChannelReferenceKind.HANDLE, _normalize_handle(text))
    return ChannelReference(ChannelReferenceKind.TITLE, text)


def normalize_channel_title(text: str) -> str:
    return " ".join(text.split()).casefold()


def channel_lookup_handle(reference: ChannelReference) -> str | None:
    if reference.kind is ChannelReferenceKind.HANDLE:
        return str(reference.value).lstrip("@")
    if reference.kind is ChannelReferenceKind.LINK:
        return _link_handle(str(reference.value))
    return None


def _is_numeric_reference(text: str) -> bool:
    return text.removeprefix("-").isdigit()


def _is_title_reference(text: str) -> bool:
    return any(text.casefold().startswith(prefix) for prefix in _TITLE_PREFIXES)


def _strip_title_prefix(text: str) -> str:
    for prefix in _TITLE_PREFIXES:
        if text.casefold().startswith(prefix):
            title = text[len(prefix) :].strip()
            if not title:
                raise ChannelReferenceResolutionError("Telegram channel title is empty")
            return title
    return text


def _is_telegram_link(text: str) -> bool:
    parsed = _parse_telegram_url(text)
    return parsed.netloc.casefold() in _TELEGRAM_HOSTS and bool(parsed.path.strip("/"))


def _is_username_reference(text: str) -> bool:
    return bool(_USERNAME_PATTERN.fullmatch(text))


def _normalize_handle(text: str) -> str:
    return text if text.startswith("@") else f"@{text}"


def _link_handle(text: str) -> str | None:
    parsed = _parse_telegram_url(text)
    path = parsed.path.strip("/")
    if not path or path.startswith("c/"):
        return None
    return path.split("/", maxsplit=1)[0]


def _parse_telegram_url(text: str):
    return urlparse(text if "://" in text else f"https://{text}")
