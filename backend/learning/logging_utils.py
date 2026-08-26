from __future__ import annotations

import logging
import traceback


class _SanitizedTracebackFilter(logging.Filter):
    """Preformat traceback locations without source lines or exception content."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "sanitized_traceback", False) or not record.exc_info:
            return True
        frames = traceback.extract_tb(record.exc_info[2])
        locations = [
            "Traceback (most recent call last):",
            *(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}' for frame in frames),
            f"{record.exc_info[0].__name__}: details suppressed",
        ]
        record.exc_text = "\n".join(locations)
        return True


def log_sanitized_exception(logger: logging.Logger, message: str, *args, exc: Exception) -> None:
    """Keep the original traceback locations while suppressing exception/input text."""
    safe_error = RuntimeError("details suppressed")
    trace_filter = _SanitizedTracebackFilter()
    logger.addFilter(trace_filter)
    try:
        logger.error(
            message + " exception_type=%s", *args, type(exc).__name__,
            exc_info=(type(safe_error), safe_error, exc.__traceback__),
            extra={"sanitized_traceback": True},
        )
    finally:
        logger.removeFilter(trace_filter)
