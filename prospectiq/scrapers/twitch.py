"""Twitch channel collection via the public GraphQL endpoint."""

from __future__ import annotations

from typing import Any

import requests

from prospectiq.config import Config
from prospectiq.constants import DEFAULT_TIMEOUT
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import raise_for_status
from prospectiq.utilities.errors import NotFoundError, ScraperError
from prospectiq.utilities.net import random_user_agent, requests_proxies
from prospectiq.utilities.text import extract_email

logger = get_logger(__name__)

SOURCE = "twitch"
GQL_URL = "https://gql.twitch.tv/gql"

#: Twitch's public web client ID, used by the site itself for anonymous reads.
PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

_QUERY = """
query ChannelProfile($login: String!) {
    user(login: $login) {
        id
        login
        displayName
        description
        followers { totalCount }
        roles { isPartner isAffiliate }
        channel { socialMedias { name url } }
    }
}
"""


def fetch(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a public Twitch channel profile.

    Falls back to a direct connection when a configured proxy fails, since
    Twitch's endpoint rejects many datacenter proxies outright.

    Args:
        identifier: Twitch username.
        config: Runtime configuration.

    Returns:
        A raw profile record, or ``None`` if the channel does not exist.
    """
    username = identifier.strip().lstrip("@").lower()
    headers = {
        "Client-ID": PUBLIC_CLIENT_ID,
        "User-Agent": random_user_agent(),
        "Accept": "application/json",
    }
    payload = {"query": _QUERY, "variables": {"login": username}}
    proxies = requests_proxies(config)

    try:
        try:
            response = requests.post(
                GQL_URL, headers=headers, json=payload, proxies=proxies, timeout=DEFAULT_TIMEOUT
            )
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError):
            if not proxies:
                raise
            logger.warning("Proxy failed for Twitch; retrying without a proxy")
            response = requests.post(
                GQL_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT
            )
    except requests.exceptions.RequestException as exc:
        raise ScraperError(
            f"Network error fetching Twitch channel {username!r}: {exc}",
            source=SOURCE,
            target=username,
        ) from exc

    raise_for_status(response.status_code, source=SOURCE, target=username)

    try:
        data = response.json()
    except ValueError as exc:
        raise ScraperError(
            f"Twitch returned a non-JSON response for {username!r}.",
            source=SOURCE,
            target=username,
        ) from exc

    if data.get("errors"):
        raise ScraperError(
            f"Twitch API error for {username!r}: {data['errors']}",
            source=SOURCE,
            target=username,
        )

    user = (data.get("data") or {}).get("user")
    if not user:
        raise NotFoundError(
            f"No public Twitch channel found for {username!r}.",
            source=SOURCE,
            target=username,
        )

    return _normalize(user, username)


def _normalize(user: dict[str, Any], username: str) -> dict[str, Any]:
    """Shape a Twitch GraphQL user object into a raw profile record."""
    bio = user.get("description") or ""
    followers = user.get("followers") or {}
    roles = user.get("roles") or {}
    channel = user.get("channel") or {}

    links = [
        social["url"]
        for social in (channel.get("socialMedias") or [])
        if isinstance(social, dict) and social.get("url")
    ]

    login = user.get("login") or username

    return {
        "platform": SOURCE,
        "username": login,
        "full_name": user.get("displayName") or "",
        "bio": bio,
        "email": extract_email(bio),
        "follower_count": (followers.get("totalCount") or 0) if followers else 0,
        "website": links[0] if links else "",
        "profile_url": f"https://twitch.tv/{login}",
        "links": links[:5],
        "is_partner": bool(roles.get("isPartner")),
        "is_affiliate": bool(roles.get("isAffiliate")),
    }
