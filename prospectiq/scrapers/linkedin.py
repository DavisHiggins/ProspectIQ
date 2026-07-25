"""LinkedIn profile collection using the operator's own session cookie.

This is the only source that requires authentication. ProspectIQ never collects,
prompts for, or stores LinkedIn credentials: the user exports their own ``li_at``
session cookie themselves and supplies it through the environment. The cookie is
read at call time and is never written to any file ProspectIQ tracks in git.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from prospectiq.config import Config
from prospectiq.constants import DEFAULT_TIMEOUT
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import raise_for_status
from prospectiq.utilities.errors import AuthenticationError, NotFoundError, ScraperError
from prospectiq.utilities.text import extract_email

logger = get_logger(__name__)

SOURCE = "linkedin"
FEED_URL = "https://www.linkedin.com/feed/"
PROFILE_API = (
    "https://www.linkedin.com/voyager/api/identity/dash/profiles"
    "?q=memberIdentity&memberIdentity={username}"
)

COOKIE_HINT = (
    "Export a fresh li_at cookie from a browser where you are logged in and set "
    "PROSPECTIQ_LINKEDIN_COOKIE."
)

MIN_COOKIE_LENGTH = 50

#: Cached authenticated session, keyed by the cookie that created it.
_session: dict[str, Any] = {"client": None, "csrf": None, "cookie": None}


def reset_session() -> None:
    """Drop the cached session. Called on auth failures and by tests."""
    client = _session.get("client")
    if client is not None:
        client.close()
    _session.update({"client": None, "csrf": None, "cookie": None})


def _open_session(cookie: str) -> tuple[httpx.Client, str]:
    """Authenticate with the supplied cookie and extract the CSRF token.

    Raises:
        AuthenticationError: The cookie is expired or rejected.
    """
    if _session["client"] is not None and _session["cookie"] == cookie:
        return _session["client"], _session["csrf"]

    reset_session()

    if len(cookie) < MIN_COOKIE_LENGTH:
        logger.warning("LinkedIn cookie looks unusually short and may be truncated")

    client = httpx.Client(follow_redirects=True, timeout=DEFAULT_TIMEOUT)
    client.cookies.set("li_at", cookie, domain=".linkedin.com")

    try:
        response = client.get(FEED_URL)
    except httpx.RequestError as exc:
        client.close()
        raise ScraperError(f"Could not reach LinkedIn: {exc}", source=SOURCE, target="") from exc

    if "login" in str(response.url) or "authwall" in str(response.url):
        client.close()
        raise AuthenticationError(
            f"LinkedIn session cookie is expired or invalid. {COOKIE_HINT}",
            source=SOURCE,
            target="",
        )

    # LinkedIn's CSRF token is the JSESSIONID cookie value, quotes included.
    csrf = next(
        (
            cookie_jar.value.strip('"')
            for cookie_jar in client.cookies.jar
            if cookie_jar.name == "JSESSIONID" and cookie_jar.value
        ),
        None,
    )
    if not csrf:
        client.close()
        raise AuthenticationError(
            f"Could not establish a LinkedIn session. {COOKIE_HINT}",
            source=SOURCE,
            target="",
        )

    _session.update({"client": client, "csrf": csrf, "cookie": cookie})
    return client, csrf


def fetch(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a LinkedIn profile visible to the operator's own session.

    Args:
        identifier: A public identifier or a full ``/in/`` profile URL.
        config: Runtime configuration; must carry a LinkedIn cookie.

    Returns:
        A raw profile record.

    Raises:
        AuthenticationError: No cookie configured, or the cookie is expired.
        NotFoundError: The profile is not visible to this session.
    """
    if not config.has_linkedin_cookie():
        raise AuthenticationError(
            f"LinkedIn requires a session cookie. {COOKIE_HINT}",
            source=SOURCE,
            target=identifier,
        )

    username = _normalize_identifier(identifier)
    client, csrf = _open_session(config.linkedin_cookie.strip())

    headers = {
        "csrf-token": csrf,
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "x-li-lang": "en_US",
        "x-restli-protocol-version": "2.0.0",
    }

    try:
        response = client.get(PROFILE_API.format(username=username), headers=headers)
    except httpx.RequestError as exc:
        raise ScraperError(
            f"Network error fetching LinkedIn profile {username!r}: {exc}",
            source=SOURCE,
            target=username,
        ) from exc

    if response.status_code == 401:
        reset_session()

    raise_for_status(response.status_code, source=SOURCE, target=username, auth_hint=COOKIE_HINT)

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise ScraperError(
            f"LinkedIn returned an unreadable response for {username!r}.",
            source=SOURCE,
            target=username,
        ) from exc

    profile = next(
        (
            item
            for item in payload.get("included", [])
            if "firstName" in item and "lastName" in item
        ),
        None,
    )
    if not profile:
        raise NotFoundError(
            f"No LinkedIn profile data visible for {username!r}.",
            source=SOURCE,
            target=username,
        )

    return _normalize(profile, username)


def _normalize_identifier(identifier: str) -> str:
    """Reduce a profile URL or handle to a bare public identifier."""
    value = identifier.strip().rstrip("/")
    if "/in/" in value:
        value = value.split("/in/")[-1]
    return value.lstrip("@").split("?")[0].strip()


def _normalize(profile: dict[str, Any], username: str) -> dict[str, Any]:
    """Shape a Voyager profile object into a raw profile record."""
    summary = profile.get("summary") or ""
    if not summary:
        localized = profile.get("multiLocaleSummary")
        if isinstance(localized, dict):
            summary = localized.get("en_US", "")

    websites = [
        w["url"] for w in profile.get("websites", []) if isinstance(w, dict) and w.get("url")
    ]

    public_id = profile.get("publicIdentifier") or username
    full_name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()

    return {
        "platform": SOURCE,
        "username": public_id,
        "full_name": full_name,
        "headline": profile.get("headline") or "",
        "bio": summary,
        "email": extract_email(summary),
        "website": websites[0] if websites else "",
        "profile_url": f"https://www.linkedin.com/in/{public_id}/",
        "is_verified": bool(profile.get("showVerificationBadge")),
        "is_premium": bool(profile.get("premium")),
        "is_influencer": bool(profile.get("influencer")),
    }
