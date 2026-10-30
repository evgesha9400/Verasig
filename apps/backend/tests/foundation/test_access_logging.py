import logging
from collections.abc import Iterator

import pytest

from verasig.foundation.http.access_logging import (
    HealthCheckAccessLogFilter,
    install_health_check_access_log_filter,
)


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:5000", "GET", path, "1.1", 200),
        exc_info=None,
    )


@pytest.fixture
def access_logger() -> Iterator[logging.Logger]:
    logger = logging.getLogger("test.uvicorn.access")
    logger.filters.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    yield logger
    logger.filters.clear()


def test_health_access_log_dropped_at_info_level(access_logger):
    access_logger.setLevel(logging.INFO)
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    assert log_filter.filter(_access_record("/health")) is False


def test_health_access_log_shown_and_relabeled_at_debug_level(access_logger):
    access_logger.setLevel(logging.DEBUG)
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    record = _access_record("/health")
    assert log_filter.filter(record) is True
    assert record.levelno == logging.DEBUG
    assert record.levelname == "DEBUG"


def test_health_path_with_query_string_is_matched(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    assert log_filter.filter(_access_record("/health?ready=1")) is False


def test_non_health_access_log_always_passes(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    record = _access_record("/api/users")
    assert log_filter.filter(record) is True
    assert record.levelname == "INFO"


def test_similar_path_is_not_treated_as_health(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    assert log_filter.filter(_access_record("/healthz")) is True


def test_non_access_record_passes_untouched(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    record = logging.LogRecord(
        name=access_logger.name,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="server started",
        args=(),
        exc_info=None,
    )
    assert log_filter.filter(record) is True


def test_install_adds_filter_once(access_logger):
    install_health_check_access_log_filter(access_logger.name)
    install_health_check_access_log_filter(access_logger.name)
    health_filters = [
        existing
        for existing in access_logger.filters
        if isinstance(existing, HealthCheckAccessLogFilter)
    ]
    assert len(health_filters) == 1


def test_sse_query_token_is_redacted_from_access_log(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    record = _access_record("/feeds/7/backfill/progress?token=eyJhbGciOi.payload.sig")

    assert log_filter.filter(record) is True
    assert record.args[2] == "/feeds/7/backfill/progress?token=[REDACTED]"
    assert "eyJhbGciOi" not in record.getMessage()


def test_query_token_redaction_keeps_other_parameters(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    record = _access_record("/progress?a=1&token=secret-jwt&b=2")

    log_filter.filter(record)

    assert record.args[2] == "/progress?a=1&token=[REDACTED]&b=2"


def test_similar_query_parameter_is_not_redacted(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    record = _access_record("/progress?mytoken=visible")

    log_filter.filter(record)

    assert record.args[2] == "/progress?mytoken=visible"


def test_mounted_health_access_log_dropped_at_info_level(access_logger):
    access_logger.setLevel(logging.INFO)
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    assert log_filter.filter(_access_record("/api/health")) is False


def test_token_query_redacted_under_api_mount(access_logger):
    log_filter = HealthCheckAccessLogFilter(access_logger.name)
    record = _access_record("/api/feeds/x/backfill/progress?token=abc")
    assert log_filter.filter(record) is True
    assert "abc" not in record.getMessage()
