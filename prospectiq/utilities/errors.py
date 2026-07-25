"""Exception hierarchy shared by every subsystem.

Scrapers raise these instead of leaking ``requests``/``httpx`` exceptions, so
the CLI can render one consistent, actionable message per failure class.
"""

from __future__ import annotations


class ProspectIQError(Exception):
    """Base class for every error raised by ProspectIQ."""


class ConfigurationError(ProspectIQError):
    """Configuration is missing or invalid — the user must fix something."""


class ScraperError(ProspectIQError):
    """A source could not be collected from."""

    def __init__(self, message: str, *, source: str = "", target: str = "") -> None:
        super().__init__(message)
        self.source = source
        self.target = target


class RateLimitedError(ScraperError):
    """The source rate limited us.

    Collection stops for that source: retrying immediately would only make the
    block worse and is exactly the behaviour ProspectIQ refuses to implement.
    """


class AuthenticationError(ScraperError):
    """The source needs credentials that are missing, expired, or rejected."""


class NotFoundError(ScraperError):
    """The requested profile does not exist or is not publicly visible."""


class BlockedError(ScraperError):
    """The source served a challenge or block page.

    Raised so the user is told plainly what happened. ProspectIQ deliberately
    implements no CAPTCHA solving or challenge-evasion behaviour.
    """


class ExportError(ProspectIQError):
    """Writing results to disk failed."""
