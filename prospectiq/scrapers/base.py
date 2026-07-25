"""Shared scraper plumbing.

Every source scraper is a callable with the signature
``fetch(identifier: str, config: Config) -> dict[str, Any] | None`` that either
returns a raw record, returns ``None`` when the profile simply is not there, or
raises a :class:`~prospectiq.utilities.errors.ScraperError` subclass.

Centralizing the HTTP call means one place decides what an HTTP 429 or 403
means, so every source reports rate limits and blocks identically.
"""

from __future__ import annotations

from typing import Any, Protocol

import requests

from prospectiq.config import Config
from prospectiq.constants import DEFAULT_TIMEOUT
from prospectiq.logging_config import get_logger
from prospectiq.utilities.errors import (
    AuthenticationError,
    BlockedError,
    NotFoundError,
    RateLimitedError,
    ScraperError,
)
from prospectiq.utilities.net import default_headers, requests_proxies

logger = get_logger(__name__)

#: Markers that indicate a challenge or block page rather than real content.
#: ProspectIQ reports these and stops; it implements no challenge solving.
BLOCK_MARKERS: tuple[str, ...] = (
    "captcha",
    "unusual traffic",
    "verify you are human",
    "access denied",
)


class SourceScraper(Protocol):
    """The interface every source scraper implements."""

    def __call__(self, identifier: str, config: Config) -> dict[str, Any] | None:
        """Collect one profile, or return ``None`` when it does not exist."""
        ...


def raise_for_status(
    status_code: int,
    *,
    source: str,
    target: str,
    auth_hint: str = "",
) -> None:
    """Translate an HTTP status code into a typed, actionable error.

    Args:
        status_code: The response status code.
        source: Source name, for the error message.
        target: The username or URL being collected.
        auth_hint: Extra guidance appended to authentication failures.

    Raises:
        NotFoundError: 404 — no such public profile.
        RateLimitedError: 429 — slow down; collection for this source stops.
        AuthenticationError: 401 — credentials missing, expired, or rejected.
        BlockedError: 403 — the source refused the request.
        ScraperError: Any other non-2xx status.
    """
    if 200 <= status_code < 300:
        return

    if status_code == 404:
        raise NotFoundError(
            f"No public {source} profile found for {target!r}.",
            source=source,
            target=target,
        )

    if status_code == 429:
        raise RateLimitedError(
            f"{source} rate limited this client. Wait a few minutes and increase "
            f"PROSPECTIQ_DELAY_MIN before trying again.",
            source=source,
            target=target,
        )

    if status_code == 401:
        message = f"{source} rejected the supplied credentials."
        if auth_hint:
            message = f"{message} {auth_hint}"
        raise AuthenticationError(message, source=source, target=target)

    if status_code == 403:
        message = (
            f"{source} refused the request for {target!r} (HTTP 403). The profile "
            f"may be private, or this client may be blocked."
        )
        if auth_hint:
            message = f"{message} {auth_hint}"
        raise BlockedError(message, source=source, target=target)

    raise ScraperError(
        f"{source} returned HTTP {status_code} for {target!r}.",
        source=source,
        target=target,
    )


def looks_blocked(html: str) -> bool:
    """Whether a response body looks like a challenge or block page."""
    if not html:
        return False
    snippet = html[:4000].lower()
    return any(marker in snippet for marker in BLOCK_MARKERS)


def fetch_html(
    url: str,
    config: Config,
    *,
    source: str,
    target: str,
    mobile: bool = False,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """GET a URL and return its body, mapping failures to typed errors.

    Raises:
        ScraperError: Or a subclass, for every failure mode including transport
            errors, which are wrapped rather than leaked as ``requests`` types.
    """
    request_headers = default_headers(mobile=mobile)
    if headers:
        request_headers.update(headers)

    try:
        response = requests.get(
            url,
            headers=request_headers,
            cookies=cookies,
            proxies=requests_proxies(config),
            timeout=timeout,
        )
    except requests.exceptions.Timeout as exc:
        raise ScraperError(
            f"Timed out fetching {source} profile {target!r}.", source=source, target=target
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ScraperError(
            f"Network error fetching {source} profile {target!r}: {exc}",
            source=source,
            target=target,
        ) from exc

    raise_for_status(response.status_code, source=source, target=target)

    body = response.text
    if looks_blocked(body):
        raise BlockedError(
            f"{source} served a challenge page for {target!r}. ProspectIQ does not "
            f"bypass challenges — wait, reduce your request rate, or try later.",
            source=source,
            target=target,
        )

    return body
