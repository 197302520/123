from __future__ import annotations

import logging


def log_sanitized_exception(logger: logging.Logger, message: str, *args, exc: Exception) -> None:
    """Keep an operational call stack while suppressing exception text and input data."""
    logger.error(message + " exception_type=%s", *args, type(exc).__name__, stack_info=True)
