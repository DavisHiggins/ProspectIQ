"""Instagram profile collection from public mobile-web HTML.

Instagram exposes no unauthenticated API, so this parses the public profile
page. It handles only public profiles: private accounts and login walls return
``None`` rather than attempting to work around the restriction.
"""

from __future__ import annotations

import re
from typing import Any

from prospectiq.config import Config
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import fetch_html
from prospectiq.utilities.errors import NotFoundError, ScraperError
from prospectiq.utilities.text import (
    decode_escapes,
    extract_email,
    extract_phone,
    parse_abbreviated_number,
)

logger = get_logger(__name__)

SOURCE = "instagram"
PROFILE_URL = "https://www.instagram.com/{username}/"

#: Instagram varies its markup, so each field is probed with several patterns
#: from most to least structured.
_PATTERNS: dict[str, tuple[str, ...]] = {
    "username": (r'"username":"([^"]+)"',),
    "full_name": (r'"full_name":"([^"]*)"', r'"name":"([^"]*)"'),
    "biography": (r'"biography":"([^"]*)"', r'"bio":"([^"]*)"'),
    "follower_count": (r'"follower_count":(\d+)', r'"edge_followed_by":\{"count":(\d+)\}'),
    "following_count": (r'"following_count":(\d+)', r'"edge_follow":\{"count":(\d+)\}'),
    "media_count": (
        r'"media_count":(\d+)',
        r'"edge_owner_to_timeline_media":\{"count":(\d+)\}',
    ),
    "external_url": (r'"external_url":"([^"]+)"', r'"website":"([^"]+)"'),
}

_META_COUNTS = re.compile(
    r"content=\"([\d.,]+[KMB]?)\s*Followers?,\s*([\d.,]+[KMB]?)\s*Following,"
    r"\s*([\d.,]+[KMB]?)\s*Posts?",
    re.IGNORECASE,
)

_NOT_FOUND_MARKERS: tuple[str, ...] = (
    "Page Not Found",
    "Sorry, this page isn",
    "The link you followed may be broken",
    "profile may have been removed",
    '"HttpErrorPage"',
)


def fetch(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a public Instagram profile.

    Args:
        identifier: Instagram username, with or without a leading ``@``.
        config: Runtime configuration.

    Returns:
        A raw profile record, or ``None`` when the page renders a login wall
        instead of public profile data.

    Raises:
        NotFoundError: The profile does not exist.
        RateLimitedError: Instagram returned HTTP 429.
        BlockedError: Instagram served a challenge page.
    """
    username = identifier.strip().lstrip("@")
    html = fetch_html(
        PROFILE_URL.format(username=username),
        config,
        source=SOURCE,
        target=username,
        mobile=True,
    )

    if any(marker in html[:10000] for marker in _NOT_FOUND_MARKERS):
        raise NotFoundError(
            f"No public Instagram profile found for @{username}.",
            source=SOURCE,
            target=username,
        )

    lowered = html[:5000].lower()
    if "/accounts/login" in lowered and "password" in lowered:
        logger.info("Instagram served a login wall for @%s; skipping", username)
        return None

    return _parse(html, username)


def _first_match(html: str, patterns: tuple[str, ...]) -> str | None:
    """Return the first capture group matched by any pattern."""
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def _parse(html: str, username: str) -> dict[str, Any] | None:
    """Extract a raw profile record from Instagram profile HTML."""
    found: dict[str, Any] = {}

    for field_name, patterns in _PATTERNS.items():
        value = _first_match(html, patterns)
        if value is not None:
            found[field_name] = value

    for count_field in ("follower_count", "following_count", "media_count"):
        if count_field in found:
            found[count_field] = parse_abbreviated_number(found[count_field])

    # Fall back to the OpenGraph description, which carries all three counts.
    meta = _META_COUNTS.search(html)
    if meta:
        for index, count_field in enumerate(("follower_count", "following_count", "media_count")):
            if not found.get(count_field):
                found[count_field] = parse_abbreviated_number(meta.group(index + 1))

    for flag, pattern in (
        ("is_verified", r'"is_verified":(true|false)'),
        ("is_private", r'"is_private":(true|false)'),
        ("is_business", r'"is_business_account":(true|false)'),
    ):
        match = re.search(pattern, html)
        if match:
            found[flag] = match.group(1) == "true"

    # A profile with no follower count means extraction failed rather than the
    # account genuinely having zero followers.
    if not found.get("follower_count"):
        raise ScraperError(
            f"Could not extract profile data for @{username}. Instagram may have "
            f"changed its page structure, or this request was throttled.",
            source=SOURCE,
            target=username,
        )

    bio = decode_escapes(found.get("biography", ""))
    website = decode_escapes((found.get("external_url") or "").replace("\\/", "/"))

    return {
        "platform": SOURCE,
        "username": found.get("username") or username,
        "full_name": decode_escapes(found.get("full_name", "")),
        "bio": bio,
        "email": extract_email(bio),
        "phone": extract_phone(bio),
        "website": website,
        "follower_count": found.get("follower_count", 0),
        "following_count": found.get("following_count", 0),
        "is_verified": found.get("is_verified", False),
        "profile_url": PROFILE_URL.format(username=username),
        "post_count": found.get("media_count", 0),
        "is_private": found.get("is_private", False),
        "is_business": found.get("is_business", False),
    }
