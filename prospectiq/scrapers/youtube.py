"""YouTube channel collection from public channel pages."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

from prospectiq.config import Config
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import fetch_html
from prospectiq.utilities.errors import ScraperError
from prospectiq.utilities.text import decode_escapes, extract_email, parse_abbreviated_number

logger = get_logger(__name__)

SOURCE = "youtube"
CHANNEL_ID_LENGTH = 24

_CONSENT_COOKIE = {"CONSENT": "PENDING+999"}

_NAME_PATTERN = re.compile(r'"channelMetadataRenderer":\{"title":"([^"]+)"')
_DESCRIPTION_PATTERN = re.compile(r'"description":"([^"]*)"')
_HANDLE_PATTERN = re.compile(r'"canonicalChannelUrl":"https://www\.youtube\.com/@([^"]+)"')
_CHANNEL_ID_PATTERN = re.compile(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"')
_BUSINESS_EMAIL_PATTERN = re.compile(r'"businessEmailLabel":\{"content":"([^"]+)"')
_LINK_PATTERN = re.compile(r'"urlEndpoint":\{"url":"(https?://[^"]+)"')

_SUBSCRIBER_PATTERNS = (
    re.compile(r'"subscriberCountText":\{"simpleText":"([\d.,]+[KMB]?) subscribers?"', re.I),
    re.compile(
        r'"subscriberCountText":\{"accessibility":\{"accessibilityData":'
        r'\{"label":"([\d.,]+[KMB]?) subscribers?"',
        re.I,
    ),
)


def _build_url(identifier: str) -> str:
    """Resolve a handle, channel ID, or custom name to a channel URL."""
    value = identifier.strip()
    if value.startswith("@"):
        return f"https://www.youtube.com/{value}"
    if value.startswith("UC") and len(value) == CHANNEL_ID_LENGTH:
        return f"https://www.youtube.com/channel/{value}"
    return f"https://www.youtube.com/@{value}"


def fetch(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a public YouTube channel profile.

    YouTube intermittently serves a consent interstitial instead of the channel
    page, so one retry is attempted with a fresh user agent before failing.

    Args:
        identifier: An ``@handle``, a ``UC...`` channel ID, or a custom name.
        config: Runtime configuration.

    Returns:
        A raw channel record.

    Raises:
        ScraperError: The channel data could not be extracted after a retry.
    """
    target = identifier.strip()
    url = _build_url(target)

    for attempt in (1, 2):
        html = fetch_html(url, config, source=SOURCE, target=target, cookies=_CONSENT_COOKIE)
        record = _parse(html, target)
        if record:
            return record
        logger.debug("YouTube returned no channel data for %s (attempt %d)", target, attempt)

    raise ScraperError(
        f"Could not extract channel data for {target!r}. YouTube may have served "
        f"a consent interstitial — try again shortly.",
        source=SOURCE,
        target=target,
    )


def _parse(html: str, identifier: str) -> dict[str, Any] | None:
    """Extract a raw channel record, or ``None`` if the page lacks channel data."""
    name_match = _NAME_PATTERN.search(html)
    if not name_match:
        return None

    description = ""
    description_match = _DESCRIPTION_PATTERN.search(html)
    if description_match:
        description = decode_escapes(description_match.group(1))

    subscribers = 0
    for pattern in _SUBSCRIBER_PATTERNS:
        match = pattern.search(html)
        if match:
            subscribers = parse_abbreviated_number(match.group(1))
            break

    handle_match = _HANDLE_PATTERN.search(html)
    handle = handle_match.group(1) if handle_match else identifier.lstrip("@")

    channel_id_match = _CHANNEL_ID_PATTERN.search(html)

    email_match = _BUSINESS_EMAIL_PATTERN.search(html)
    email = email_match.group(1) if email_match else extract_email(description)

    links: list[str] = []
    for match in _LINK_PATTERN.finditer(html):
        link = _resolve_redirect(match.group(1))
        is_external = link and "youtube.com" not in link and "google.com" not in link
        if is_external and link not in links:
            links.append(link)

    return {
        "platform": SOURCE,
        "username": handle,
        "full_name": decode_escapes(name_match.group(1)),
        "bio": description,
        "email": email,
        "follower_count": subscribers,
        "website": links[0] if links else "",
        "profile_url": f"https://www.youtube.com/@{handle}",
        "links": links[:5],
        "channel_id": channel_id_match.group(1) if channel_id_match else "",
    }


def _resolve_redirect(url: str) -> str:
    """Unwrap YouTube's outbound redirect URLs to the real destination."""
    if "youtube.com/redirect" not in url:
        return url
    match = re.search(r"[?&]q=([^&]+)", url)
    return unquote(match.group(1)) if match else ""
