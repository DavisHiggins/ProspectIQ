"""The source registry.

One declarative table describes every supported source: how to collect from it,
whether it needs authentication, and how to label it in the CLI. Adding a source
means adding a module and one :class:`Source` entry — nothing else in the
codebase enumerates sources by hand.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from prospectiq.config import Config
from prospectiq.logging_config import get_logger
from prospectiq.models import Lead
from prospectiq.scrapers import (
    github,
    instagram,
    linkbio,
    linkedin,
    pinterest,
    tiktok,
    twitch,
    youtube,
)
from prospectiq.utilities.errors import ConfigurationError

logger = get_logger(__name__)

FetchFn = Callable[[str, Config], "dict[str, Any] | None"]


@dataclass(frozen=True)
class Source:
    """A supported collection source.

    Attributes:
        key: Stable identifier used in exports and CLI arguments.
        label: Human-readable name for display.
        fetch: The collection callable.
        requires_auth: Whether the source needs operator-supplied credentials.
        input_label: What the user is asked to supply.
        notes: Known limitations, surfaced in the CLI and README.
    """

    key: str
    label: str
    fetch: FetchFn
    requires_auth: bool = False
    input_label: str = "Username"
    notes: str = ""

    def is_available(self, config: Config) -> tuple[bool, str]:
        """Whether this source can run under the current configuration.

        Returns:
            ``(available, reason)``; ``reason`` is empty when available.
        """
        if self.requires_auth and self.key == "linkedin" and not config.has_linkedin_cookie():
            return False, "PROSPECTIQ_LINKEDIN_COOKIE is not set"
        return True, ""


SOURCES: dict[str, Source] = {
    "instagram": Source(
        key="instagram",
        label="Instagram",
        fetch=instagram.fetch,
        notes="Public profiles only; may throttle by region or IP.",
    ),
    "tiktok": Source(
        key="tiktok",
        label="TikTok",
        fetch=tiktok.fetch,
        notes="May serve a challenge page depending on region or IP.",
    ),
    "linkedin": Source(
        key="linkedin",
        label="LinkedIn",
        fetch=linkedin.fetch,
        requires_auth=True,
        input_label="Username or profile URL",
        notes="Requires your own li_at session cookie, which expires periodically.",
    ),
    "github": Source(
        key="github",
        label="GitHub",
        fetch=github.fetch,
        notes="Public REST API, limited to 60 requests/hour unauthenticated.",
    ),
    "youtube": Source(
        key="youtube",
        label="YouTube",
        fetch=youtube.fetch,
        input_label="Channel handle or ID",
        notes="Accepts @handle or UC... channel IDs.",
    ),
    "twitch": Source(
        key="twitch",
        label="Twitch",
        fetch=twitch.fetch,
        notes="Falls back to a direct connection when a proxy fails.",
    ),
    "linkbio": Source(
        key="linkbio",
        label="Link-in-bio",
        fetch=linkbio.fetch,
        notes="Tries Linktree, Stan, Linkr, and Bio.link in order.",
    ),
    "pinterest": Source(
        key="pinterest",
        label="Pinterest",
        fetch=pinterest.fetch,
        notes="Public profiles only.",
    ),
}


def get_source(key: str) -> Source:
    """Look up a source by key.

    Raises:
        ConfigurationError: The key is not a supported source.
    """
    normalized = key.strip().lower()
    if normalized not in SOURCES:
        raise ConfigurationError(
            f"Unknown source {key!r}. Supported sources: {', '.join(SOURCES)}."
        )
    return SOURCES[normalized]


def source_keys() -> list[str]:
    """Return every supported source key, in registry order."""
    return list(SOURCES)


def collect(source_key: str, identifier: str, config: Config) -> Lead | None:
    """Collect one profile and normalize it into a :class:`Lead`.

    This is the single entry point the CLI and demo mode use. Scraper errors
    propagate to the caller so it can decide whether to continue the run.

    Args:
        source_key: Which source to collect from.
        identifier: The username, handle, or URL to collect.
        config: Runtime configuration.

    Returns:
        A normalized lead, or ``None`` when the profile carried no usable data.
    """
    source = get_source(source_key)

    available, reason = source.is_available(config)
    if not available:
        raise ConfigurationError(f"{source.label} is unavailable: {reason}")

    raw = source.fetch(identifier, config)
    if not raw:
        return None

    return Lead.from_raw(raw, source=source.key)
