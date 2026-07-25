"""Transparent lead and email scoring.

Both scores are deliberately simple, additive, and capped at 100. Nothing here
is a model or a black box: every point is traceable to a named signal, which is
the only honest way to present a "quality score" derived from public data.
"""

from __future__ import annotations

from prospectiq.constants import BUYER_INTENT_KEYWORDS, EMAIL_SOURCE_SCORES
from prospectiq.models import Lead

MAX_SCORE = 100

# --- Lead score weights ---------------------------------------------------

POINTS_EMAIL = 30
POINTS_PHONE = 30
POINTS_WEBSITE = 10
POINTS_VERIFIED_ACCOUNT = 10
POINTS_BUYER_INTENT = 5
POINTS_COMPANY_KNOWN = 5

#: Follower bands. Mid-sized accounts score highest: large enough to be an
#: established business, small enough to still read their own inbox.
FOLLOWER_BANDS: tuple[tuple[int, int, int], ...] = (
    (5_000, 50_000, 15),
    (1_000, 100_000, 10),
    (1, 10_000_000_000, 5),
)

# --- Email confidence adjustments -----------------------------------------

BONUS_SMTP_CONFIRMED = 10
PENALTY_CATCH_ALL = 20
BONUS_PATTERN_CORROBORATED = 15
BONUS_PATTERN_WEAK = 10
PATTERN_STRONG_EVIDENCE = 3


def calculate_lead_score(lead: Lead) -> int:
    """Score a lead 0-100 on how actionable it is.

    The score answers "how much usable contact information do we have, and does
    this look like a decision-maker?" — not "how likely is this person to buy".

    Args:
        lead: The enriched lead.

    Returns:
        A score from 0 to 100.
    """
    score = 0

    if lead.email:
        score += POINTS_EMAIL
    if lead.phone:
        score += POINTS_PHONE
    if lead.website:
        score += POINTS_WEBSITE
    if lead.is_verified:
        score += POINTS_VERIFIED_ACCOUNT
    if lead.company or lead.company_domain:
        score += POINTS_COMPANY_KNOWN

    for low, high, points in FOLLOWER_BANDS:
        if low <= lead.follower_count <= high:
            score += points
            break

    haystack = f"{lead.biography} {lead.headline}".lower()
    if any(keyword in haystack for keyword in BUYER_INTENT_KEYWORDS):
        score += POINTS_BUYER_INTENT

    return min(score, MAX_SCORE)


def score_email_candidate(
    source: str,
    *,
    smtp_confirmed: bool = False,
    catch_all: bool = False,
    corroborating_emails: int = 0,
) -> int:
    """Score an email candidate 0-100 on how likely it is to be correct.

    A high score means the address is well-evidenced, not that it was verified.
    Only ``smtp_confirmed`` reflects an actual mailbox check, and a catch-all
    domain cancels most of that value because such servers accept everything.

    Args:
        source: Where the candidate came from, e.g. ``"bio"`` or ``"pattern"``.
        smtp_confirmed: The mail server accepted this specific address.
        catch_all: The domain accepts mail for any address, so acceptance
            proves nothing.
        corroborating_emails: How many addresses on the same domain were
            observed. Only strengthens pattern-derived guesses.

    Returns:
        A confidence score from 0 to 100.
    """
    score = EMAIL_SOURCE_SCORES.get(source, 0)

    if source == "pattern" and corroborating_emails:
        score += (
            BONUS_PATTERN_CORROBORATED
            if corroborating_emails >= PATTERN_STRONG_EVIDENCE
            else BONUS_PATTERN_WEAK
        )

    if smtp_confirmed:
        score += BONUS_SMTP_CONFIRMED
    if catch_all:
        score -= PENALTY_CATCH_ALL

    return max(0, min(score, MAX_SCORE))
