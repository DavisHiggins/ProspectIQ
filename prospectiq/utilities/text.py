"""Text parsing helpers shared by every scraper and the enrichment pipeline."""

from __future__ import annotations

import re

from prospectiq.constants import (
    EMAIL_DOMAIN_BLACKLIST,
    EMAIL_REGEX,
    FILE_EXTENSION_BLACKLIST,
)

_EMAIL_PATTERN = re.compile(EMAIL_REGEX)

_PHONE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\+1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
    re.compile(r"\+?\d{1,3}[-.\s]\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
    re.compile(r"\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}"),
    re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),
)

_TEL_LINK_PATTERN = re.compile(r"""href=["']tel:([+\d\s\-().]+)""")
_WHATSAPP_PATTERN = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\d+)")
_SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL)
_STYLE_PATTERN = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"{}|\\^`\[\]]+"
    r"|(?:linktr\.ee|stan\.store|beacons\.ai)/[^\s<>\"{}|\\^`\[\]]+"
)

_NUMBER_SUFFIXES: dict[str, int] = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

MIN_PHONE_DIGITS = 10
MAX_PHONE_DIGITS = 15


def is_valid_email(email: str) -> bool:
    """Whether an email looks like a real contact rather than page furniture.

    Filters placeholder domains (``example.com``), third-party service domains
    that appear in markup (``sentry.io``), and asset filenames that the email
    regex matches by accident.
    """
    if not email or "@" not in email:
        return False
    lowered = email.lower()
    if any(blocked in lowered for blocked in EMAIL_DOMAIN_BLACKLIST):
        return False
    return not lowered.endswith(FILE_EXTENSION_BLACKLIST)


def extract_emails(text: str) -> list[str]:
    """Return every plausible, de-duplicated email in ``text``, in page order."""
    if not text:
        return []

    seen: set[str] = set()
    found: list[str] = []
    for match in _EMAIL_PATTERN.findall(text):
        lowered = match.lower()
        if lowered not in seen and is_valid_email(match):
            seen.add(lowered)
            found.append(match)
    return found


def extract_email(text: str) -> str:
    """Return the first plausible email in ``text``, or an empty string."""
    emails = extract_emails(text)
    return emails[0] if emails else ""


def strip_html(text: str) -> str:
    """Reduce HTML to its visible text, dropping scripts, styles, and tags."""
    if not text:
        return ""
    visible = _SCRIPT_PATTERN.sub(" ", text)
    visible = _STYLE_PATTERN.sub(" ", visible)
    visible = _TAG_PATTERN.sub(" ", visible)
    return re.sub(r"\s+", " ", visible).strip()


def extract_phone(text: str) -> str:
    """Extract the most reliable phone number available in ``text``.

    Explicit ``tel:`` and WhatsApp links are preferred over numbers matched in
    free text, which are far more likely to be dates, prices, or IDs.
    """
    if not text:
        return ""

    tel_links: list[str] = _TEL_LINK_PATTERN.findall(text)
    for tel in tel_links:
        digits = re.sub(r"[^\d+]", "", tel)
        if MIN_PHONE_DIGITS <= len(digits.lstrip("+")) <= MAX_PHONE_DIGITS:
            return tel.strip()

    whatsapp_numbers: list[str] = _WHATSAPP_PATTERN.findall(text)
    for number in whatsapp_numbers:
        if MIN_PHONE_DIGITS <= len(number) <= MAX_PHONE_DIGITS:
            return f"+{number}"

    visible = strip_html(text) if "<" in text else text
    for pattern in _PHONE_PATTERNS:
        candidates: list[str] = pattern.findall(visible)
        for candidate in candidates:
            digits = re.sub(r"[^\d+]", "", candidate)
            if MIN_PHONE_DIGITS <= len(digits.lstrip("+")) <= MAX_PHONE_DIGITS:
                return candidate.strip()

    return ""


def extract_urls(text: str) -> list[str]:
    """Return normalized URLs mentioned in ``text``, stripped of trailing punctuation."""
    if not text:
        return []

    urls: list[str] = []
    seen: set[str] = set()
    for raw in _URL_PATTERN.findall(text):
        url = raw.rstrip(".,;:!?)")
        if not url.startswith("http"):
            url = f"https://{url}"
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def parse_abbreviated_number(value: str) -> int:
    """Parse counts like ``"11.5K"``, ``"2.3M"``, or ``"1,204"`` into an int.

    Returns ``0`` for anything unparseable, since these values come from
    scraped markup and a bad parse must never crash a collection run.
    """
    if not value:
        return 0

    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return 0

    suffix = cleaned[-1].upper()
    if suffix in _NUMBER_SUFFIXES:
        try:
            return int(float(cleaned[:-1]) * _NUMBER_SUFFIXES[suffix])
        except ValueError:
            return 0

    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def decode_escapes(text: str) -> str:
    """Decode ``\\uXXXX`` escapes found in scraped JSON-in-HTML payloads.

    Returns the input unchanged when it is not decodable, which is preferable
    to raising on one malformed bio.
    """
    if not text:
        return ""
    try:
        return (
            text.encode("utf-8")
            .decode("unicode_escape")
            .encode("utf-16", "surrogatepass")
            .decode("utf-16")
        )
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def truncate(text: str, limit: int, suffix: str = "...") -> str:
    """Shorten ``text`` to ``limit`` characters for terminal display."""
    if not text or len(text) <= limit:
        return text or ""
    return text[: max(limit - len(suffix), 0)] + suffix
