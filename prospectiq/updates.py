"""Optional release-update check.

Deliberately conservative, and different from the upstream project's behaviour
in three ways:

1. It is **opt-in**. It only runs when ``PROSPECTIQ_UPDATE_CHECK=true``, so the
   tool makes no outbound request the user did not ask for.
2. It is **advisory**. A newer release prints a note; it never blocks or exits.
3. It points at the ProspectIQ repository, never at any upstream project.
"""

from __future__ import annotations

from prospectiq import __version__
from prospectiq.constants import RELEASES_API_URL, REPO_URL
from prospectiq.logging_config import get_logger

logger = get_logger(__name__)

REQUEST_TIMEOUT = 3.0


def parse_version(value: str) -> tuple[int, ...]:
    """Parse a dotted version into a comparable tuple.

    Unparseable input becomes ``(0,)``, which sorts below any real release.
    """
    cleaned = value.strip().lstrip("vV").split("-")[0].split("+")[0]
    parts: list[int] = []
    for chunk in cleaned.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            break
    return tuple(parts) if parts else (0,)


def is_newer(candidate: str, current: str = __version__) -> bool:
    """Whether ``candidate`` is a strictly newer version than ``current``."""
    return parse_version(candidate) > parse_version(current)


def check_for_update(enabled: bool = False) -> str | None:
    """Look for a newer published release.

    Args:
        enabled: When ``False`` (the default) no request is made at all.

    Returns:
        The newer version string, or ``None``. Never raises: an update check
        failing is not a reason for the tool to fail.
    """
    if not enabled:
        return None

    try:
        import requests

        response = requests.get(
            RELEASES_API_URL,
            headers={"Accept": "application/vnd.github+json"},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            logger.debug("Update check returned HTTP %s", response.status_code)
            return None

        tag = str(response.json().get("tag_name", ""))
    except Exception as exc:
        logger.debug("Update check failed: %s", exc)
        return None

    if tag and is_newer(tag):
        return tag.lstrip("vV")
    return None


def update_message(latest: str) -> str:
    """Render the advisory shown when a newer release exists."""
    return f"ProspectIQ {latest} is available (you have {__version__}). See {REPO_URL}/releases"
