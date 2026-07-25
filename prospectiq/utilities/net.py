"""HTTP client helpers: user agents, proxy selection, pacing, and retries.

This module replaces the upstream ``stealth`` module. The rename is deliberate:
nothing here evades detection, solves challenges, or impersonates a logged-in
user. It rotates a small set of ordinary browser user agents, optionally routes
through a user-supplied proxy, and paces requests so ProspectIQ behaves like a
polite client.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TypeVar

import requests

from prospectiq.config import Config
from prospectiq.constants import DEFAULT_MAX_RETRIES
from prospectiq.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

#: Current-generation desktop browser user agents. Requests sent without any
#: user agent are rejected by most sources, so one is always supplied.
USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
)

MOBILE_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Mobile Safari/537.36",
)

_FREE_PROXY_TTL_SECONDS = 300
_free_proxy_cache: list[str] = []
_free_proxy_fetched_at: float = 0.0


def random_user_agent(mobile: bool = False) -> str:
    """Return a random browser user agent string."""
    return random.choice(MOBILE_USER_AGENTS if mobile else USER_AGENTS)


def default_headers(mobile: bool = False) -> dict[str, str]:
    """Return the baseline request headers used by every scraper."""
    return {
        "User-Agent": random_user_agent(mobile=mobile),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def polite_delay(delay_range: tuple[float, float]) -> None:
    """Sleep for a random interval inside ``delay_range``.

    Called between requests so a collection run does not hammer a source.
    """
    low, high = delay_range
    time.sleep(random.uniform(low, max(high, low)))


def _read_proxy_file(path: Path) -> list[str]:
    """Read a newline-delimited proxy list, ignoring blanks and comments."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("Could not read proxy file %s: %s", path, exc)
        return []
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def _fetch_free_proxies() -> list[str]:
    """Fetch a short-lived pool of free public proxies.

    Free proxies are unreliable by nature; results are cached briefly so a run
    does not re-fetch them for every request.
    """
    global _free_proxy_cache, _free_proxy_fetched_at

    if _free_proxy_cache and (time.time() - _free_proxy_fetched_at) < _FREE_PROXY_TTL_SECONDS:
        return _free_proxy_cache

    try:
        from fp.fp import FreeProxy
    except ImportError:
        logger.debug("free-proxy is not installed; skipping free proxy lookup")
        return []

    proxies: list[str] = []
    for _ in range(5):
        try:
            found = FreeProxy(timeout=1, rand=True, anonym=True).get()
        except Exception as exc:
            logger.debug("Free proxy lookup failed: %s", exc)
            continue
        if found:
            proxies.append(found)

    if proxies:
        _free_proxy_cache = proxies
        _free_proxy_fetched_at = time.time()
        logger.info("Fetched %d free proxies", len(proxies))

    return proxies


def select_proxy(config: Config) -> str:
    """Choose a proxy URL for the next request, or return an empty string.

    Resolution order: explicit URL, then a random entry from the proxy file,
    then the free proxy pool if enabled.
    """
    if config.proxy_url:
        return config.proxy_url

    if config.proxy_file:
        proxies = _read_proxy_file(config.proxy_file)
        if proxies:
            return random.choice(proxies)

    if config.use_free_proxy:
        free = _fetch_free_proxies()
        if free:
            return random.choice(free)

    return ""


def _normalize_proxy(proxy: str) -> str:
    """Ensure a proxy string carries a scheme."""
    if not proxy:
        return ""
    return proxy if proxy.startswith("http") else f"http://{proxy}"


def httpx_proxy(config: Config) -> str | None:
    """Return a proxy URL formatted for ``httpx``, or ``None``."""
    return _normalize_proxy(select_proxy(config)) or None


def requests_proxies(config: Config) -> dict[str, str] | None:
    """Return a proxy mapping formatted for ``requests``, or ``None``."""
    proxy = _normalize_proxy(select_proxy(config))
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def test_connection(config: Config, timeout: float = 10.0) -> tuple[bool, str]:
    """Check outbound connectivity through the configured proxy.

    Returns:
        ``(ok, detail)`` where ``detail`` is the observed egress IP on success
        or a truncated error message on failure.
    """
    proxies = requests_proxies(config)
    try:
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            timeout=timeout,
            headers={"User-Agent": random_user_agent()},
        )
        response.raise_for_status()
        return True, str(response.json().get("origin", "unknown"))
    except Exception as exc:
        return False, str(exc)[:120]


def with_retries(
    max_attempts: int = DEFAULT_MAX_RETRIES,
    backoff: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """Retry a function on transient network errors with linear backoff.

    Only connection-level failures are retried. HTTP-level rejections such as
    rate limits and auth failures are raised immediately, because retrying them
    is both useless and rude.

    Args:
        max_attempts: Total attempts, including the first.
        backoff: Seconds multiplied by the attempt number between retries.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T | None:
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (
                    requests.exceptions.ProxyError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                ) as exc:
                    last_error = exc
                    logger.warning(
                        "%s (attempt %d/%d): %s",
                        type(exc).__name__,
                        attempt,
                        max_attempts,
                        exc,
                    )
                    if attempt < max_attempts:
                        time.sleep(backoff * attempt)
            logger.error("All %d attempts failed: %s", max_attempts, last_error)
            return None

        return wrapper

    return decorator
