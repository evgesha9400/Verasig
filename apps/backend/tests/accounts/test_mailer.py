import logging
from email.message import EmailMessage

import pytest

from verasig.config import MailConfig
from verasig.features.accounts import mailer as mailer_module
from verasig.features.accounts.mailer import (
    LogMailer,
    SmtpMailer,
    build_password_reset_email,
    create_mailer,
    send_email_confirm,
)

RESET_URL = "https://verasig.test/reset-password?token=secret-jwt-token"


def _config(tls: str) -> MailConfig:
    return MailConfig(
        host="smtp.example.com",
        port=465,
        user="resend",
        password="key",
        tls=tls,
        sender="Verasig <no-reply@verasig.io>",
    )


class _FakeSmtp:
    instances: list["_FakeSmtp"] = []

    def __init__(self, host, port, timeout):
        self.address = (host, port)
        self.calls: list[str] = []
        self.sent: list[EmailMessage] = []
        _FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(f"login:{user}")

    def send_message(self, message):
        self.sent.append(message)


@pytest.fixture
def fake_smtp(monkeypatch):
    _FakeSmtp.instances = []
    monkeypatch.setattr(mailer_module.smtplib, "SMTP", _FakeSmtp)
    monkeypatch.setattr(mailer_module.smtplib, "SMTP_SSL", _FakeSsl)
    return _FakeSmtp


class _FakeSsl(_FakeSmtp):
    pass


def test_send_email_confirm_never_logs_the_token(caplog):
    # the email-change token is a bearer credential; it must not reach the logs.
    with caplog.at_level(logging.INFO):
        send_email_confirm("user@example.com", "secret-jwt-token")

    record = next(
        r for r in caplog.records if r.getMessage() == "email confirmation requested"
    )
    assert not hasattr(record, "token")
    assert "secret-jwt-token" not in caplog.text


def test_password_reset_email_carries_the_link_once_per_part():
    message = build_password_reset_email("ada@example.com", RESET_URL)

    assert message["To"] == "ada@example.com"
    assert message["Subject"] == "Reset your Verasig password"
    text = message.get_body(("plain",)).get_content()
    html = message.get_body(("html",)).get_content()
    assert text.count(RESET_URL) == 1
    assert html.count(RESET_URL) == 1
    assert "60 minutes" in text
    assert "ignore" in text.lower()


def test_smtp_mailer_uses_ssl_and_logs_in(fake_smtp):
    message = build_password_reset_email("ada@example.com", RESET_URL)

    SmtpMailer(_config("ssl")).send(message)

    (smtp,) = fake_smtp.instances
    assert isinstance(smtp, _FakeSsl)
    assert smtp.address == ("smtp.example.com", 465)
    assert smtp.calls == ["login:resend"]
    assert smtp.sent == [message]
    assert message["From"] == "Verasig <no-reply@verasig.io>"


def test_smtp_mailer_upgrades_with_starttls(fake_smtp):
    SmtpMailer(_config("starttls")).send(
        build_password_reset_email("ada@example.com", RESET_URL)
    )

    (smtp,) = fake_smtp.instances
    assert not isinstance(smtp, _FakeSsl)
    assert smtp.calls == ["starttls", "login:resend"]


def test_smtp_mailer_sends_plain_without_login_when_no_user(fake_smtp):
    config = MailConfig(
        host="mailpit",
        port=1025,
        user="",
        password="",
        tls="none",
        sender="Verasig <no-reply@verasig.io>",
    )

    SmtpMailer(config).send(build_password_reset_email("ada@example.com", RESET_URL))

    (smtp,) = fake_smtp.instances
    assert not isinstance(smtp, _FakeSsl)
    assert smtp.calls == []
    assert len(smtp.sent) == 1


def test_log_mailer_never_logs_the_link(caplog):
    with caplog.at_level(logging.INFO):
        LogMailer().send(build_password_reset_email("ada@example.com", RESET_URL))

    (record,) = caplog.records
    assert record.email == "ada@example.com"
    assert "secret-jwt-token" not in caplog.text
    assert "secret-jwt-token" not in str(vars(record))


def test_create_mailer_picks_log_mailer_without_config():
    assert isinstance(create_mailer(None), LogMailer)
    assert isinstance(create_mailer(_config("ssl")), SmtpMailer)
