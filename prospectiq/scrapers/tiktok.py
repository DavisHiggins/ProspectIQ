"""TikTok profile collection from the public profile page."""

from __future__ import annotations

import json
import re
from typing import Any

from prospectiq.config import Config
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import fetch_html
from prospectiq.utilities.errors import ScraperError
from prospectiq.utilities.text import extract_email

logger = get_logger(__name__)

SOURCE = "tiktok"
PROFILE_URL = "https://www.tiktok.com/@{username}"

#: TikTok embeds its page state as JSON in this script tag.
_REHYDRATION_PATTERN = re.compile(
    r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
    re.DOTALL,
)


def fetch(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a public TikTok profile.

    Args:
        identifier: TikTok username, with or without a leading ``@``.
        config: Runtime configuration.

    Returns:
        A raw profile record.

    Raises:
        BlockedError: TikTok served a CAPTCHA or challenge page. This is common
            from datacenter IPs; ProspectIQ reports it rather than solving it.
        ScraperError: The page did not contain the expected data structure.
    """
    username = identifier.strip().lstrip("@")
    url = PROFILE_URL.format(username=username)

    html = fetch_html(url, config, source=SOURCE, target=username)

    match = _REHYDRATION_PATTERN.search(html)
    if not match:
        raise ScraperError(
            f"TikTok did not return profile data for @{username}. This usually "
            f"means the request was challenged or the page structure changed.",
            source=SOURCE,
            target=username,
        )

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ScraperError(
            f"Could not parse TikTok profile data for @{username}.",
            source=SOURCE,
            target=username,
        ) from exc

    try:
        user_info = payload["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
    except (KeyError, TypeError) as exc:
        raise ScraperError(
            f"Unexpected TikTok response structure for @{username}.",
            source=SOURCE,
            target=username,
        ) from exc

    user = user_info.get("user") or {}
    stats = user_info.get("stats") or {}
    bio = user.get("signature") or ""

    return {
        "platform": SOURCE,
        "username": user.get("uniqueId") or username,
        "full_name": user.get("nickname") or "",
        "bio": bio,
        "email": extract_email(bio),
        "profile_url": url,
        "is_verified": bool(user.get("verified")),
        "follower_count": stats.get("followerCount", 0),
        "following_count": stats.get("followingCount", 0),
        "likes_count": stats.get("heartCount", 0),
        "video_count": stats.get("videoCount", 0),
    }
