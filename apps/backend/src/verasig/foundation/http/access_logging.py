import logging

UVICORN_ACCESS_LOGGER_NAME = "uvicorn.access"
HEALTH_PATH = "/health"
_FULL_PATH_ARG_INDEX = 2


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


class HealthCheckAccessLogFilter(logging.Filter):
    """Demote uvicorn /health access logs so they surface only under DEBUG."""

    def __init__(self, logger_name: str = UVICORN_ACCESS_LOGGER_NAME) -> None:
        super().__init__()
        self._logger_name = logger_name

    def filter(self, record: logging.LogRecord) -> bool:
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
