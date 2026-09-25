"""Project-wide constants.

Everything here is a value that used to be scattered as a string literal across
the codebase. Keeping them in one module makes the branding, the network
etiquette defaults, and the export schema auditable in a single place.
"""

from __future__ import annotations

from typing import Final

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

APP_NAME: Final[str] = "ProspectIQ"
APP_TAGLINE: Final[str] = "Open-Source Lead Intelligence"
APP_DESCRIPTION: Final[str] = (
    "Open-source lead intelligence that turns public profiles into structured, "
    "traceable, locally controlled records."
)

MAINTAINER: Final[str] = "Davis Higgins"
MAINTAINER_PORTFOLIO: Final[str] = "https://davishiggins.com"
MAINTAINER_GITHUB: Final[str] = "https://github.com/davishiggins"
COMPANY_NAME: Final[str] = "Higgins Digital"
COMPANY_URL: Final[str] = "https://higginsd.com"

REPO_SLUG: Final[str] = "davishiggins/prospectiq"
REPO_URL: Final[str] = f"https://github.com/{REPO_SLUG}"
ISSUES_URL: Final[str] = f"{REPO_URL}/issues"
RELEASES_API_URL: Final[str] = f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"

# ProspectIQ is a rebranded, independently maintained derivative of the MIT
# licensed "Scout" project. Recorded here for attribution only — no runtime
# code should point at the upstream repository.
UPSTREAM_PROJECT: Final[str] = "Scout"
UPSTREAM_REPO_URL: Final[str] = "https://github.com/kiryano/Scout"

# --------------------------------------------------------------------------
# Brand palette — dark navy, intelligence teal, and signal gold
# --------------------------------------------------------------------------

CANVAS_MIDNIGHT: Final[str] = "#001019"
DEEP_NAVY: Final[str] = "#0E272F"
STRUCTURAL_NAVY: Final[str] = "#143D49"
GLASS_TEAL: Final[str] = "#225E6A"
INTELLIGENCE_TEAL: Final[str] = "#2999A3"
SOFT_CYAN: Final[str] = "#9CC6CF"
SIGNAL_GOLD: Final[str] = "#C9B171"
BRIGHT_GOLD: Final[str] = "#D6A84B"
SOFT_WHITE: Final[str] = "#F5F8FA"
MUTED_SLATE: Final[str] = "#8FA5B0"

STYLE_SUCCESS: Final[str] = "green"
STYLE_WARNING: Final[str] = "yellow"
STYLE_ERROR: Final[str] = "red"
STYLE_BODY: Final[str] = "white"
STYLE_MUTED: Final[str] = "dim"

# --------------------------------------------------------------------------
# Environment variables
# --------------------------------------------------------------------------

ENV_PREFIX: Final[str] = "PROSPECTIQ_"
LEGACY_ENV_PREFIX: Final[str] = "SCOUT_"

ENV_FILE_NAME: Final[str] = ".env"

# --------------------------------------------------------------------------
# Network etiquette defaults
# --------------------------------------------------------------------------
# Deliberately conservative. ProspectIQ favours being a polite client over
# raw throughput; users who need different pacing must opt in explicitly.

DEFAULT_DELAY_MIN: Final[float] = 2.0
DEFAULT_DELAY_MAX: Final[float] = 5.0
MIN_ALLOWED_DELAY: Final[float] = 0.5

DEFAULT_TIMEOUT: Final[float] = 20.0
DEFAULT_MAX_RETRIES: Final[int] = 3

#: Per-source delay overrides (min, max) in seconds, applied when the user has
#: not configured an explicit delay. Sources with stricter rate limits wait
#: longer between requests.
SOURCE_DELAYS: Final[dict[str, tuple[float, float]]] = {
    "instagram": (2.5, 5.0),
    "tiktok": (3.0, 6.0),
    "linkedin": (4.0, 8.0),
    "github": (1.0, 2.0),
    "youtube": (2.0, 4.0),
    "twitch": (1.0, 2.5),
    "pinterest": (2.0, 4.0),
    "linktree": (1.0, 2.5),
}

# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR: Final[str] = "exports"
EXPORT_PREFIX: Final[str] = "prospectiq_leads"
DEMO_OUTPUT_DIR: Final[str] = "demo_output"

#: Stable, documented CSV column order. Any additional per-source fields are
#: appended after these, sorted alphabetically, so the core schema never moves.
CSV_CORE_FIELDS: Final[tuple[str, ...]] = (
    "source",
    "username",
    "display_name",
    "profile_url",
    "biography",
    "website",
    "email",
    "email_confidence",
    "email_source",
    "email_verified",
    "phone",
    "company",
    "company_domain",
    "headline",
    "location",
    "follower_count",
    "following_count",
    "is_verified",
    "lead_score",
    "collected_at",
)

# --------------------------------------------------------------------------
# Enrichment
# --------------------------------------------------------------------------

EMAIL_REGEX: Final[str] = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

#: Domains that appear in page source but never belong to a real lead.
EMAIL_DOMAIN_BLACKLIST: Final[tuple[str, ...]] = (
    "example.com",
    "test.com",
    "email.com",
    "youremail.com",
    "sentry.io",
    "wixpress.com",
    "googleapis.com",
    "w3.org",
    "schema.org",
    "gravatar.com",
    "wordpress.com",
)

FILE_EXTENSION_BLACKLIST: Final[tuple[str, ...]] = (
    ".png",
    ".jpg",
    ".gif",
    ".css",
    ".js",
    ".svg",
    ".webp",
    ".ico",
)

#: A "website" pointing at one of these is a social profile, not a company site,
#: so it is not worth deep-scraping for contact details.
NON_COMPANY_DOMAINS: Final[tuple[str, ...]] = (
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "linktr.ee",
    "stan.store",
    "beacons.ai",
    "bit.ly",
    "spotify.com",
)

#: Paths probed when deep-scraping a lead's website for contact information.
CONTACT_PAGE_PATHS: Final[tuple[str, ...]] = (
    "",
    "/contact",
    "/contact-us",
    "/about",
    "/about-us",
)

#: HELO / MAIL FROM identity used during SMTP existence checks. It is a
#: non-routable identifier: ProspectIQ never sends mail.
SMTP_HELO_HOST: Final[str] = "prospectiq-verify.local"
SMTP_MAIL_FROM: Final[str] = f"verify@{SMTP_HELO_HOST}"
SMTP_TIMEOUT: Final[float] = 10.0

#: Confidence contribution by where an email candidate came from.
EMAIL_SOURCE_SCORES: Final[dict[str, int]] = {
    "bio": 90,
    "hunter.io": 80,
    "website": 70,
    "smtp_guess": 70,
    "bio_link": 65,
    "contact_page": 60,
    "pattern": 40,
}

#: Bio keywords that suggest a decision-maker or business owner.
BUYER_INTENT_KEYWORDS: Final[tuple[str, ...]] = (
    "coach",
    "consultant",
    "ceo",
    "founder",
    "entrepreneur",
    "agency",
    "business",
    "owner",
    "director",
    "manager",
)
