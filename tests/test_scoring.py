"""Lead scoring and email confidence."""

from __future__ import annotations

import pytest

from prospectiq.enrichment.scoring import (
    MAX_SCORE,
    calculate_lead_score,
    score_email_candidate,
)
from prospectiq.models import Lead


def make_lead(**overrides: object) -> Lead:
    """Build a bare lead with specific fields overridden."""
    defaults: dict[str, object] = {"source": "github", "username": "x"}
    return Lead(**{**defaults, **overrides})  # type: ignore[arg-type]


class TestLeadScore:
    def test_empty_lead_scores_zero(self) -> None:
        assert calculate_lead_score(make_lead()) == 0

    def test_email_contributes(self) -> None:
        assert calculate_lead_score(make_lead(email="a@b.co")) == 30

    def test_phone_contributes(self) -> None:
        assert calculate_lead_score(make_lead(phone="+15555550142")) == 30

    def test_contact_details_stack(self) -> None:
        lead = make_lead(email="a@b.co", phone="+15555550142")

        assert calculate_lead_score(lead) == 60

    def test_website_and_verification_add_points(self) -> None:
        lead = make_lead(website="https://example.org", is_verified=True)

        assert calculate_lead_score(lead) == 20

    @pytest.mark.parametrize(
        ("followers", "expected"),
        [(0, 0), (500, 5), (2_000, 10), (20_000, 15), (500_000, 5)],
    )
    def test_follower_bands(self, followers: int, expected: int) -> None:
        """Mid-sized accounts are the most valuable, so they score highest."""
        assert calculate_lead_score(make_lead(follower_count=followers)) == expected

    def test_buyer_intent_keywords_in_bio(self) -> None:
        assert calculate_lead_score(make_lead(biography="Founder and coach")) == 5

    def test_buyer_intent_keywords_in_headline(self) -> None:
        assert calculate_lead_score(make_lead(headline="CEO at Acme")) == 5

    def test_keyword_matching_is_case_insensitive(self) -> None:
        assert calculate_lead_score(make_lead(biography="FOUNDER")) == 5

    def test_company_information_adds_points(self) -> None:
        assert calculate_lead_score(make_lead(company="Acme Corp")) == 5

    def test_score_never_exceeds_the_maximum(self) -> None:
        lead = make_lead(
            email="a@b.co",
            phone="+15555550142",
            website="https://example.org",
            is_verified=True,
            company="Acme",
            company_domain="acme.example",
            follower_count=20_000,
            biography="Founder, CEO, consultant, agency owner",
        )

        assert calculate_lead_score(lead) == MAX_SCORE

    def test_fully_enriched_lead_outranks_a_bare_one(self) -> None:
        rich = make_lead(email="a@b.co", phone="+1555", follower_count=20_000)
        bare = make_lead(follower_count=20_000)

        assert calculate_lead_score(rich) > calculate_lead_score(bare)


class TestEmailConfidence:
    def test_bio_addresses_score_highest(self) -> None:
        """An address the person published themselves is the strongest signal."""
        assert score_email_candidate("bio") > score_email_candidate("pattern")

    @pytest.mark.parametrize(
        ("source", "expected"),
        [("bio", 90), ("hunter.io", 80), ("website", 70), ("bio_link", 65), ("pattern", 40)],
    )
    def test_base_scores_by_source(self, source: str, expected: int) -> None:
        assert score_email_candidate(source) == expected

    def test_unknown_source_scores_zero(self) -> None:
        assert score_email_candidate("made-up") == 0

    def test_smtp_confirmation_adds_confidence(self) -> None:
        assert score_email_candidate("website", smtp_confirmed=True) == 80

    def test_catch_all_domain_reduces_confidence(self) -> None:
        """A catch-all accepts everything, so acceptance proves nothing."""
        assert score_email_candidate("website", smtp_confirmed=True, catch_all=True) == 60

    def test_corroborating_addresses_strengthen_a_pattern_guess(self) -> None:
        weak = score_email_candidate("pattern", corroborating_emails=1)
        strong = score_email_candidate("pattern", corroborating_emails=5)

        assert strong > weak > score_email_candidate("pattern")

    def test_corroboration_does_not_inflate_observed_addresses(self) -> None:
        """Only inferred addresses benefit from corroboration."""
        assert score_email_candidate("bio", corroborating_emails=5) == 90

    def test_score_is_clamped_to_the_valid_range(self) -> None:
        high = score_email_candidate("bio", smtp_confirmed=True, corroborating_emails=9)
        low = score_email_candidate("pattern", catch_all=True)

        assert 0 <= low <= high <= MAX_SCORE
