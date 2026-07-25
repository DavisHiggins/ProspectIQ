"""Pinterest profile collection from public profile pages."""

from __future__ import annotations

import json
import re
from typing import Any

from prospectiq.config import Config
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import fetch_html
from prospectiq.utilities.errors import NotFoundError
from prospectiq.utilities.text import decode_escapes, extract_email

logger = get_logger(__name__)

SOURCE = "pinterest"
PROFILE_URL = "https://www.pinterest.com/{username}/"

MAX_SEARCH_DEPTH = 15

_PWS_PATTERN = re.compile(r'<script[^>]*id="__PWS_DATA__"[^>]*>(.*?)</script>', re.DOTALL)

_FALLBACK_PATTERNS: dict[str, str] = {
    "full_name": r'"full_name":"([^"]+)"',
    "bio": r'"about":"([^"]*)"',
    "website": r'"website_url":"([^"]+)"',
}

_COUNT_PATTERNS: dict[str, str] = {
    "follower_count": r'"follower_count":(\d+)',
    "following_count": r'"following_count":(\d+)',
    "pin_count": r'"pin_count":(\d+)',
    "board_count": r'"board_count":(\d+)',
}

_NOT_FOUND_MARKERS = ("User not found", "This page isn't available")


def fetch(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a public Pinterest profile.

    Args:
        identifier: Pinterest username.
        config: Runtime configuration.

    Returns:
        A raw profile record, or ``None`` if the page contained no profile data.

    Raises:
        NotFoundError: The profile does not exist.
    """
    username = identifier.strip().lstrip("@").lower()
    html = fetch_html(PROFILE_URL.format(username=username), config, source=SOURCE, target=username)

    if any(marker in html for marker in _NOT_FOUND_MARKERS):
        raise NotFoundError(
            f"No public Pinterest profile found for {username!r}.",
            source=SOURCE,
            target=username,
        )

    return _parse(html, username)


def _parse(html: str, username: str) -> dict[str, Any] | None:
    """Extract a raw profile record from Pinterest HTML."""
    found: dict[str, Any] = {}

    pws_match = _PWS_PATTERN.search(html)
    if pws_match:
        try:
            payload = json.loads(pws_match.group(1))
        except json.JSONDecodeError:
            logger.debug("Could not parse Pinterest __PWS_DATA__ for %s", username)
        else:
            user = _find_user(payload, username)
            if user:
                found.update(user)

    for field_name, pattern in _FALLBACK_PATTERNS.items():
        if not found.get(field_name):
            match = re.search(pattern, html)
            if match:
                found[field_name] = decode_escapes(match.group(1)).replace("\\/", "/")

    for field_name, pattern in _COUNT_PATTERNS.items():
        if not found.get(field_name):
            match = re.search(pattern, html)
            if match:
                found[field_name] = int(match.group(1))

    if not found.get("full_name") and not found.get("follower_count"):
        logger.info("Pinterest page for %s contained no profile data", username)
        return None

    bio = found.get("bio", "")

    return {
        "platform": SOURCE,
        "username": username,
        "full_name": found.get("full_name", ""),
        "bio": bio,
        "email": extract_email(bio),
        "website": found.get("website", ""),
        "follower_count": found.get("follower_count", 0),
        "following_count": found.get("following_count", 0),
        "is_verified": bool(re.search(r'"is_verified_merchant":true', html)),
        "profile_url": PROFILE_URL.format(username=username),
        "pin_count": found.get("pin_count", 0),
        "board_count": found.get("board_count", 0),
    }


def _find_user(data: Any, username: str, depth: int = 0) -> dict[str, Any] | None:
    """Recursively locate the user object inside Pinterest's page state."""
    if depth > MAX_SEARCH_DEPTH:
        return None

    if isinstance(data, dict):
        candidate = str(data.get("username", "")).lower()
        if candidate == username.lower() and "follower_count" in data:
            return {
                "full_name": data.get("full_name", ""),
                "bio": data.get("about", ""),
                "follower_count": data.get("follower_count", 0),
                "following_count": data.get("following_count", 0),
                "website": data.get("website_url", ""),
                "pin_count": data.get("pin_count", 0),
                "board_count": data.get("board_count", 0),
            }
        for value in data.values():
            found = _find_user(value, username, depth + 1)
            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = _find_user(item, username, depth + 1)
            if found:
                return found

    return None
