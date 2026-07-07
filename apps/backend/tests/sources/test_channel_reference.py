import pytest

from verasig.domain.channel_reference import (
    ChannelReferenceKind,
    ChannelReferenceResolutionError,
    channel_lookup_handle,
    parse_channel_reference,
)


def test_parse_channel_reference_accepts_handle_and_bare_handle():
    assert parse_channel_reference("@pilot").kind is ChannelReferenceKind.HANDLE
    bare = parse_channel_reference("pilot_signals")
    assert bare.kind is ChannelReferenceKind.HANDLE
    assert bare.value == "@pilot_signals"


def test_parse_channel_reference_accepts_telegram_link():
    parsed = parse_channel_reference("https://t.me/pilot_signals")
    assert parsed.kind is ChannelReferenceKind.LINK
    assert channel_lookup_handle(parsed) == "pilot_signals"


@pytest.mark.parametrize(
    "link",
    [
        "https://t.me/joinchat/AAAAAEHbBc",
        "https://t.me/+AbCdEf123",
        "https://t.me/c/1234567890",
    ],
)
def test_invite_and_private_links_have_no_public_handle(link):
    # joinchat/…, +… and c/… links are private invites, not @-usernames.
    parsed = parse_channel_reference(link)
    assert parsed.kind is ChannelReferenceKind.LINK
    assert channel_lookup_handle(parsed) is None


def test_parse_channel_reference_accepts_numeric_id():
    parsed = parse_channel_reference("123")
    assert parsed.kind is ChannelReferenceKind.ID
    assert parsed.value == 123


def test_parse_channel_reference_accepts_explicit_title():
    parsed = parse_channel_reference("title:Signals")
    assert parsed.kind is ChannelReferenceKind.TITLE
    assert parsed.value == "Signals"


def test_parse_channel_reference_treats_non_username_text_as_title():
    parsed = parse_channel_reference("Математик. Трейдинг и инвестиции.")
    assert parsed.kind is ChannelReferenceKind.TITLE


def test_parse_channel_reference_rejects_empty_title_selector():
    with pytest.raises(ChannelReferenceResolutionError, match="title is empty"):
        parse_channel_reference("title:")
