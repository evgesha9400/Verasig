import logging

from verasig.features.accounts.mailer import send_email_confirm


def test_send_email_confirm_never_logs_the_token(caplog):
    # the email-change token is a bearer credential; it must not reach the logs.
    with caplog.at_level(logging.INFO):
        send_email_confirm("user@example.com", "secret-jwt-token")

    record = next(
        r for r in caplog.records if r.getMessage() == "email confirmation requested"
    )
    assert not hasattr(record, "token")
    assert "secret-jwt-token" not in caplog.text
