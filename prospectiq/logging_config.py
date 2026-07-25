"""Centralized logging setup.

The CLI is the only caller of :func:`configure_logging`. Library modules just
call ``logging.getLogger(__name__)`` and never configure handlers themselves.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager

LOGGER_NAMESPACE = "prospectiq"

_QUIET_FORMAT = "%(levelname)s: %(message)s"
_VERBOSE_FORMAT = "%(asctime)s %(name)s %(levelname)s: %(message)s"


def configure_logging(verbose: bool = False) -> None:
    """Install a single stderr handler for the application.

    Args:
        verbose: Emit ``DEBUG`` records with timestamps instead of warnings only.

    Logging goes to stderr so that it never contaminates piped stdout output.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_VERBOSE_FORMAT if verbose else _QUIET_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Third-party HTTP clients are chatty at DEBUG and drown out our own records.
    for noisy in ("httpx", "httpcore", "urllib3", "requests"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger for a module."""
    return logging.getLogger(name)


@contextmanager
def suppressed_logging(active: bool = True) -> Iterator[None]:
    """Temporarily silence logging below ``CRITICAL``.

    Used around interactive progress spinners, where a stray warning would
    corrupt the rendered output. Restores the previous level on exit, including
    when the body raises.

    Args:
        active: When ``False`` the context manager does nothing, so callers can
            write ``with suppressed_logging(not verbose):``.
    """
    if not active:
        yield
        return

    root = logging.getLogger()
    previous = root.level
    root.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        root.setLevel(previous)
