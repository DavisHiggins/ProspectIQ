"""The normalized lead record.

Every scraper returns a raw dictionary shaped by whatever the source happens to
provide. :meth:`Lead.from_raw` folds those varying shapes into one schema, so
enrichment, scoring, and export never need to know which source a record came
from. Fields a source provides but the core schema does not model are kept in
:attr:`Lead.extra` rather than discarded.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any

from prospectiq.constants import CSV_CORE_FIELDS

#: Raw scraper key -> canonical :class:`Lead` field.
FIELD_ALIASES: dict[str, str] = {
    "platform": "source",
    "full_name": "display_name",
    "name": "display_name",
    "bio": "biography",
    "description": "biography",
    "email_score": "email_confidence",
    "subscribers": "follower_count",
    "subscriber_count": "follower_count",
    "verified": "is_verified",
}

#: Keys that carry no analytical value once normalized.
DROPPED_KEYS: frozenset[str] = frozenset({"possible_emails"})


def _utc_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Lead:
    """A single normalized prospect record.

    Attributes:
        source: Which source the record came from, e.g. ``"github"``.
        username: The handle on that source. Always present.
        display_name: Human-readable name, when the source exposes one.
        profile_url: Canonical URL of the public profile.
        biography: Profile bio or description text.
        website: Best external URL found on the profile.
        email: The highest-confidence email candidate, if any.
        email_confidence: Confidence in ``email``, 0-100. See
            :mod:`prospectiq.enrichment.scoring` for how it is derived.
        email_source: Where ``email`` came from, e.g. ``"bio"`` or ``"pattern"``.
        email_verified: True only when an SMTP check positively confirmed the
            mailbox. False means unconfirmed, never "invalid".
        phone: Phone number found on the profile or linked pages.
        company: Employer name, when stated.
        company_domain: Domain resolved for ``company`` via DNS MX lookup.
        headline: Professional headline, where the source has one.
        location: Self-reported location.
        follower_count: Followers or subscribers.
        following_count: Accounts followed.
        is_verified: Whether the source marks the account as verified.
        lead_score: Transparent 0-100 quality score.
        collected_at: UTC ISO-8601 timestamp of collection.
        extra: Source-specific fields preserved outside the core schema.
    """

    source: str
    username: str
    display_name: str = ""
    profile_url: str = ""
    biography: str = ""
    website: str = ""
    email: str = ""
    email_confidence: int = 0
    email_source: str = ""
    email_verified: bool = False
    phone: str = ""
    company: str = ""
    company_domain: str = ""
    headline: str = ""
    location: str = ""
    follower_count: int = 0
    following_count: int = 0
    is_verified: bool = False
    lead_score: int = 0
    collected_at: str = field(default_factory=_utc_timestamp)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def core_field_names(cls) -> tuple[str, ...]:
        """Return the canonical field names, excluding ``extra``."""
        return tuple(f.name for f in fields(cls) if f.name != "extra")

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source: str = "") -> Lead:
        """Normalize a raw scraper dictionary into a :class:`Lead`.

        Unknown keys land in :attr:`extra` instead of being dropped, and values
        are coerced to the declared types so a source returning ``None`` or a
        string count cannot corrupt downstream scoring or export.

        Args:
            raw: The dictionary a scraper returned.
            source: Source name, used when ``raw`` does not carry one.

        Returns:
            A normalized lead.

        Raises:
            ValueError: If neither ``raw`` nor ``source`` identifies a source.
        """
        mapped: dict[str, Any] = {}
        extra: dict[str, Any] = {}
        known = set(cls.core_field_names())

        for key, value in raw.items():
            if key in DROPPED_KEYS:
                continue
            canonical = FIELD_ALIASES.get(key, key)
            if canonical in known:
                # An alias must not overwrite an explicitly provided canonical key.
                if canonical not in mapped or mapped[canonical] in ("", 0, False, None):
                    mapped[canonical] = value
            elif value not in (None, "", [], {}):
                extra[key] = value

        resolved_source = str(mapped.get("source") or source or "").strip()
        if not resolved_source:
            raise ValueError("Cannot build a Lead without a source")

        username = str(mapped.get("username") or "").strip()
        if not username:
            raise ValueError(f"Cannot build a {resolved_source} Lead without a username")

        return cls(
            source=resolved_source,
            username=username,
            display_name=_as_text(mapped.get("display_name")),
            profile_url=_as_text(mapped.get("profile_url")),
            biography=_as_text(mapped.get("biography")),
            website=_as_text(mapped.get("website")),
            email=_as_text(mapped.get("email")),
            email_confidence=_as_int(mapped.get("email_confidence")),
            email_source=_as_text(mapped.get("email_source")),
            email_verified=bool(mapped.get("email_verified", False)),
            phone=_as_text(mapped.get("phone")),
            company=_as_text(mapped.get("company")),
            company_domain=_as_text(mapped.get("company_domain")),
            headline=_as_text(mapped.get("headline")),
            location=_as_text(mapped.get("location")),
            follower_count=_as_int(mapped.get("follower_count")),
            following_count=_as_int(mapped.get("following_count")),
            is_verified=bool(mapped.get("is_verified", False)),
            lead_score=_as_int(mapped.get("lead_score")),
            collected_at=_as_text(mapped.get("collected_at")) or _utc_timestamp(),
            extra=extra,
        )

    def to_dict(self, *, flatten_extra: bool = True) -> dict[str, Any]:
        """Render the lead as a flat dictionary suitable for CSV export.

        Args:
            flatten_extra: Merge scalar values from :attr:`extra` into the
                result. Nested values are JSON-ish stringified so a CSV cell
                never contains a Python ``repr``.
        """
        row: dict[str, Any] = {name: getattr(self, name) for name in CSV_CORE_FIELDS}

        if flatten_extra:
            for key, value in self.extra.items():
                if key in row:
                    continue
                row[key] = _stringify(value)

        return row

    @property
    def has_contact(self) -> bool:
        """Whether the lead carries any directly usable contact detail."""
        return bool(self.email or self.phone)

    def __str__(self) -> str:
        label = self.display_name or self.username
        return f"{label} ({self.source}/@{self.username})"


def _as_text(value: Any) -> str:
    """Coerce a scraped value to a stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: Any) -> int:
    """Coerce a scraped value to an int, defaulting to ``0``."""
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return int(value)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _stringify(value: Any) -> Any:
    """Flatten nested values for a single CSV cell."""
    if isinstance(value, (list, tuple)):
        return "; ".join(_stringify(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):
        return "; ".join(f"{k}={_stringify(v)}" for k, v in value.items() if v not in (None, ""))
    return value
