"""Reusable helpers: text parsing, HTTP plumbing, and the error hierarchy."""

from prospectiq.utilities.errors import (
    AuthenticationError,
    BlockedError,
    ConfigurationError,
    ExportError,
    NotFoundError,
    ProspectIQError,
    RateLimitedError,
    ScraperError,
)
from prospectiq.utilities.text import (
    decode_escapes,
    extract_email,
    extract_emails,
    extract_phone,
    extract_urls,
    is_valid_email,
    parse_abbreviated_number,
    strip_html,
    truncate,
)

__all__ = [
    "AuthenticationError",
    "BlockedError",
    "ConfigurationError",
    "ExportError",
    "NotFoundError",
    "ProspectIQError",
    "RateLimitedError",
    "ScraperError",
    "decode_escapes",
    "extract_email",
    "extract_emails",
    "extract_phone",
    "extract_urls",
    "is_valid_email",
    "parse_abbreviated_number",
    "strip_html",
    "truncate",
]
