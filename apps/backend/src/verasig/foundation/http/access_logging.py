import logging
import re

UVICORN_ACCESS_LOGGER_NAME = "uvicorn.access"
APP_LOGGER_NAME = "verasig"
_APP_HANDLER_NAME = "verasig_app_handler"
HEALTH_PATH = "/health"
_FULL_PATH_ARG_INDEX = 2
# SSE routes authenticate with `?token=<jwt>` (EventSource cannot set headers);
# the bearer token must never reach the access log in clear.
_QUERY_TOKEN = re.compile(r"([?&]token=)[^&#\s]+")
_REDACTED = r"\1[REDACTED]"


def configure_app_logging(level: int = logging.INFO) -> None:
    """Emit `verasig.*` logs at INFO on their own stream handler (idempotent).

    Uvicorn only configures its own loggers, leaving the root at WARNING, so
    application INFO logs are otherwise swallowed. Attach a dedicated handler
    once and stop propagation to avoid duplicate lines via the root logger.
    """
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(level)
    if any(handler.name == _APP_HANDLER_NAME for handler in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.set_name(_APP_HANDLER_NAME)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False


def _record_request_path(record: logging.LogRecord) -> str | None:
    args = record.args
    if not isinstance(args, tuple) or len(args) <= _FULL_PATH_ARG_INDEX:
        return None
    full_path = args[_FULL_PATH_ARG_INDEX]
    if not isinstance(full_path, str):
        return None
    return full_path.split("?", 1)[0]


def _is_health_access_record(record: logging.LogRecord) -> bool:
    return _record_request_path(record) == HEALTH_PATH


def _redact_query_token(record: logging.LogRecord) -> None:
    args = record.args
    if not isinstance(args, tuple) or len(args) <= _FULL_PATH_ARG_INDEX:
        return
    full_path = args[_FULL_PATH_ARG_INDEX]
    if not isinstance(full_path, str):
        return
    redacted = _QUERY_TOKEN.sub(_REDACTED, full_path)
    if redacted != full_path:
        index = _FULL_PATH_ARG_INDEX
        record.args = (*args[:index], redacted, *args[index + 1 :])


class HealthCheckAccessLogFilter(logging.Filter):
    """Demote uvicorn /health access logs so they surface only under DEBUG, and
    redact `?token=` query credentials from every access line."""

    def __init__(self, logger_name: str = UVICORN_ACCESS_LOGGER_NAME) -> None:
        super().__init__()
        self._logger_name = logger_name

    def filter(self, record: logging.LogRecord) -> bool:
        _redact_query_token(record)
        if not _is_health_access_record(record):
            return True
        self._relabel_as_debug(record)
        return self._debug_logging_enabled()

    def _relabel_as_debug(self, record: logging.LogRecord) -> None:
        record.levelno = logging.DEBUG
        record.levelname = "DEBUG"

    def _debug_logging_enabled(self) -> bool:
        logger = logging.getLogger(self._logger_name)
        return logger.getEffectiveLevel() <= logging.DEBUG


def _filter_already_installed(logger: logging.Logger) -> bool:
    return any(
        isinstance(existing, HealthCheckAccessLogFilter) for existing in logger.filters
    )


def install_health_check_access_log_filter(
    logger_name: str = UVICORN_ACCESS_LOGGER_NAME,
) -> None:
    """Attach the health-check access-log filter to the uvicorn access logger once."""
    logger = logging.getLogger(logger_name)
    if _filter_already_installed(logger):
        return
    logger.addFilter(HealthCheckAccessLogFilter(logger_name))
