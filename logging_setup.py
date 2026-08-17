"""Shared logging configuration for Dutchkem Model 4.0.

All modules use ``logging.getLogger("dutchkem.<name>")`` and this helper
installs one stream handler on the ``dutchkem`` parent logger. Level is
controlled by ``LOG_LEVEL`` (default INFO)."""

import logging
import os
import sys

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s %(message)s"


def setup_logging(level: str = None) -> logging.Logger:
    """Configure (once) and return the ``dutchkem`` parent logger."""
    level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger("dutchkem")
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)
    root.propagate = False
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``dutchkem`` namespace."""
    return logging.getLogger(f"dutchkem.{name}")


def log_exception(logger: logging.Logger, exc: BaseException, context: str = ""):
    """Log an exception with full traceback (never re-raises)."""
    logger.exception("error while %s: %s", context or "handling request", exc)
