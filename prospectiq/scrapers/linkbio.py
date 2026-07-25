"""Link-in-bio page collection.

Covers Linktree and several compatible services. These pages are the single
richest public source of contact details, because their whole purpose is to
publish the ways someone wants to be reached.
"""

from __future__ import annotations

import json
import re
from typing import Any

from prospectiq.config import Config
from prospectiq.logging_config import get_logger
from prospectiq.scrapers.base import fetch_html
from prospectiq.utilities.errors import NotFoundError, ScraperError
from prospectiq.utilities.text import extract_email

logger = get_logger(__name__)

SOURCE = "linkbio"

#: Supported link-in-bio services, in the order ``fetch`` tries them.
PROVIDERS: dict[str, str] = {
    "linktree": "https://linktr.ee/{username}",
    "stan": "https://stan.store/{username}",
    "linkr": "https://linkr.bio/{username}",
    "biolink": "https://bio.link/{username}",
}

MAX_LINKS = 20

_NEXT_DATA_PATTERN = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
_HREF_PATTERN = re.compile(r'href="((?:https?://|mailto:)[^"]+)"')
_TITLE_PATTERN = re.compile(r"<title>([^<]+)</title>")
_META_DESCRIPTION_PATTERN = re.compile(r'<meta[^>]*name="description"[^>]*content="([^"]*)"')

#: Handle patterns for recognising social profiles among a page's links.
_SOCIAL_PATTERNS: dict[str, str] = {
    "instagram": r"instagram\.com/([^/?]+)",
    "twitter": r"(?:twitter|x)\.com/([^/?]+)",
    "tiktok": r"tiktok\.com/@?([^/?]+)",
    "youtube": r"youtube\.com/(?:@|c/|channel/)?([^/?]+)",
    "twitch": r"twitch\.tv/([^/?]+)",
    "github": r"github\.com/([^/?]+)",
    "linkedin": r"linkedin\.com/in/([^/?]+)",
    "spotify": r"open\.spotify\.com/(?:artist|user)/([^/?]+)",
    "soundcloud": r"soundcloud\.com/([^/?]+)",
}

#: Domains that are social profiles rather than a personal or company website.
_SOCIAL_DOMAINS: tuple[str, ...] = (
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "twitch.tv",
    "github.com",
    "linkedin.com",
    "spotify.com",
    "soundcloud.com",
    "facebook.com",
    "pinterest.com",
    "snapchat.com",
    "reddit.com",
    "stan.store",
    "linktr.ee",
    "linkr.bio",
    "bio.link",
)

_SKIP_URL_MARKERS = ("favicon", "static", "assets", ".css", ".js")


def fetch(identifier: str, config: Config, provider: str = "") -> dict[str, Any] | None:
    """Collect a link-in-bio page.

    Args:
        identifier: The username on the service.
        config: Runtime configuration.
        provider: A specific provider key from :data:`PROVIDERS`. When empty,
            every provider is tried in order and the first hit is returned.

    Returns:
        A raw profile record.

    Raises:
        NotFoundError: No provider had a page for this username.
        ScraperError: An unknown provider key was supplied.
    """
    username = identifier.strip().lstrip("@").lower()

    if provider and provider not in PROVIDERS:
        raise ScraperError(
            f"Unknown link-in-bio provider {provider!r}. Supported: {', '.join(PROVIDERS)}.",
            source=SOURCE,
            target=username,
        )

    providers = [provider] if provider else list(PROVIDERS)

    for name in providers:
        try:
            html = fetch_html(
                PROVIDERS[name].format(username=username),
                config,
                source=name,
                target=username,
            )
        except NotFoundError:
            continue

        record = _parse(html, username, name)
        if record:
            return record

    raise NotFoundError(
        f"No link-in-bio page found for {username!r} on {', '.join(providers)}.",
        source=SOURCE,
        target=username,
    )


def fetch_linktree(identifier: str, config: Config) -> dict[str, Any] | None:
    """Collect a Linktree page specifically."""
    return fetch(identifier, config, provider="linktree")


def _parse(html: str, username: str, provider: str) -> dict[str, Any] | None:
    """Parse a link-in-bio page, preferring structured data where available."""
    if provider == "linktree":
        record = _parse_linktree(html, username)
        if record:
            return record
    return _parse_generic(html, username, provider)


def _parse_linktree(html: str, username: str) -> dict[str, Any] | None:
    """Parse Linktree's embedded Next.js page state."""
    match = _NEXT_DATA_PATTERN.search(html)
    if not match:
        return None

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.debug("Could not parse Linktree __NEXT_DATA__ for %s", username)
        return None

    account = payload.get("props", {}).get("pageProps", {}).get("account") or {}
    if not account:
        return None

    links = [
        {"title": link.get("title", ""), "url": link["url"]}
        for link in account.get("links", [])
        if isinstance(link, dict) and link.get("url")
    ]
    bio = account.get("description") or ""

    return _build_record(
        username=username,
        provider="linktree",
        full_name=account.get("pageTitle") or "",
        bio=bio,
        links=links,
        profile_url=f"https://linktr.ee/{username}",
    )


def _parse_generic(html: str, username: str, provider: str) -> dict[str, Any] | None:
    """Parse any link-in-bio page by harvesting its outbound links."""
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    for url in _HREF_PATTERN.findall(html):
        if url in seen or any(marker in url for marker in _SKIP_URL_MARKERS):
            continue
        seen.add(url)
        links.append({"title": "", "url": url})

    if not links:
        return None

    title_match = _TITLE_PATTERN.search(html)
    description_match = _META_DESCRIPTION_PATTERN.search(html)

    return _build_record(
        username=username,
        provider=provider,
        full_name=title_match.group(1).strip() if title_match else "",
        bio=description_match.group(1) if description_match else "",
        links=links,
        profile_url=PROVIDERS[provider].format(username=username),
    )


def _build_record(
    *,
    username: str,
    provider: str,
    full_name: str,
    bio: str,
    links: list[dict[str, str]],
    profile_url: str,
) -> dict[str, Any]:
    """Assemble the raw record shared by every link-in-bio parser."""
    socials = _extract_socials(links)

    return {
        "platform": SOURCE,
        "username": username,
        "full_name": full_name,
        "bio": bio,
        "email": _email_from_links(links) or extract_email(bio),
        "website": _personal_website(links),
        "profile_url": profile_url,
        "provider": provider,
        "link_count": len(links),
        "links": [link["url"] for link in links[:MAX_LINKS]],
        **{f"social_{name}": handle for name, handle in socials.items()},
    }


def _extract_socials(links: list[dict[str, str]]) -> dict[str, str]:
    """Map recognised social platforms to the handle found for each."""
    socials: dict[str, str] = {}
    for link in links:
        url = link.get("url", "")
        for platform, pattern in _SOCIAL_PATTERNS.items():
            if platform in socials:
                continue
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                socials[platform] = match.group(1)
    return socials


def _personal_website(links: list[dict[str, str]]) -> str:
    """Return the first link that is a real website rather than a social profile."""
    for link in links:
        url = link.get("url", "")
        if not url.startswith("http"):
            continue
        if not any(domain in url.lower() for domain in _SOCIAL_DOMAINS):
            return url
    return ""


def _email_from_links(links: list[dict[str, str]]) -> str:
    """Extract an address from a ``mailto:`` link, if present."""
    for link in links:
        url = link.get("url", "")
        if url.startswith("mailto:"):
            return url.removeprefix("mailto:").split("?")[0]
    return ""
