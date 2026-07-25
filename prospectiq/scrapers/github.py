"""GitHub profile collection via the public REST API.

Uses the documented, unauthenticated ``/users/{username}`` endpoint, which is
limited to 60 requests per hour per IP.
"""

from __future__ import annotations

from typing import Any

import requests

from prospectiq.config import Config
from prospectiq.constants import DEFAULT_TIMEOUT
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import raise_for_status
from prospectiq.utilities.errors import RateLimitedError, ScraperError
from prospectiq.utilities.net import random_user_agent, requests_proxies
from prospectiq.utilities.text import extract_email

logger = get_logger(__name__)

SOURCE = "github"
API_URL = "https://api.github.com/users/{username}"


def fetch(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a public GitHub profile.

    Args:
        identifier: GitHub username.
        config: Runtime configuration.

    Returns:
        A raw profile record, or ``None`` if the account carries no usable
        profile information at all.

    Raises:
        NotFoundError: The user does not exist.
        RateLimitedError: The 60/hour unauthenticated quota is exhausted.
        ScraperError: Any other failure.
    """
    username = identifier.strip().lstrip("@")
    url = API_URL.format(username=username)

    try:
        response = requests.get(
            url,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": random_user_agent(),
            },
            proxies=requests_proxies(config),
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise ScraperError(
            f"Network error fetching GitHub profile {username!r}: {exc}",
            source=SOURCE,
            target=username,
        ) from exc

    # GitHub signals quota exhaustion with 403 plus a zeroed remaining header,
    # which is a rate limit rather than an authorization problem.
    if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        raise RateLimitedError(
            "GitHub API rate limit reached (60 requests/hour unauthenticated). "
            "Wait for the window to reset before collecting more profiles.",
            source=SOURCE,
            target=username,
        )

    raise_for_status(response.status_code, source=SOURCE, target=username)

    try:
        data = response.json()
    except ValueError as exc:
        raise ScraperError(
            f"GitHub returned a non-JSON response for {username!r}.",
            source=SOURCE,
            target=username,
        ) from exc

    signals = (
        data.get("name"),
        data.get("bio"),
        data.get("email"),
        data.get("blog"),
        data.get("company"),
        data.get("twitter_username"),
    )
    if not any(signals):
        logger.info("GitHub user @%s has an empty profile; skipping", username)
        return None

    bio = data.get("bio") or ""

    return {
        "platform": SOURCE,
        "username": data.get("login") or username,
        "full_name": data.get("name") or "",
        "bio": bio,
        "email": data.get("email") or extract_email(bio),
        "company": (data.get("company") or "").lstrip("@"),
        "location": data.get("location") or "",
        "website": data.get("blog") or "",
        "follower_count": data.get("followers", 0),
        "following_count": data.get("following", 0),
        "profile_url": data.get("html_url") or f"https://github.com/{username}",
        "public_repos": data.get("public_repos", 0),
        "twitter": data.get("twitter_username") or "",
        "is_hireable": bool(data.get("hireable")),
    }
