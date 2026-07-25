"""Email pattern inference and SMTP verification, all offline."""

from __future__ import annotations

import pytest

from prospectiq.enrichment.email_patterns import (
    apply_pattern,
    detect_pattern,
    extract_domain,
    generate_candidates,
    infer_from_observed,
    split_name,
)
from prospectiq.enrichment.smtp_verify import VerificationResult, verify_email


class TestDomainExtraction:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("https://www.example.org/about", "example.org"),
            ("http://example.org", "example.org"),
            ("example.org", "example.org"),
            ("https://sub.example.co.uk/x?y=1", "sub.example.co.uk"),
            ("https://example.org:8443/", "example.org"),
        ],
    )
    def test_normalizes_urls_to_domains(self, raw: str, expected: str) -> None:
        assert extract_domain(raw) == expected

    def test_empty_input_yields_empty_output(self) -> None:
        assert extract_domain("") == ""


class TestNameSplitting:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Jane Doe", ("jane", "doe")),
            ("Jane Q. Doe", ("jane", "doe")),
            ("  JANE   DOE  ", ("jane", "doe")),
            ("Jane O'Brien", ("jane", "obrien")),
        ],
    )
    def test_splits_into_first_and_last(self, name: str, expected: tuple[str, str]) -> None:
        assert split_name(name) == expected

    @pytest.mark.parametrize("name", ["", "Cher", "   ", "123"])
    def test_unusable_names_yield_empty_parts(self, name: str) -> None:
        assert split_name(name) == ("", "")


class TestPatternDetection:
    @pytest.mark.parametrize(
        ("local", "expected"),
        [
            ("jane.doe", "first.last"),
            ("j.doe", "f.last"),
            ("jane", "first"),
            ("jane_doe", "first_last"),
        ],
    )
    def test_infers_structure_without_a_reference_name(self, local: str, expected: str) -> None:
        assert detect_pattern(local) == expected

    @pytest.mark.parametrize(
        ("local", "expected"),
        [
            ("jane.doe", "first.last"),
            ("janedoe", "firstlast"),
            ("jdoe", "flast"),
            ("j.doe", "f.last"),
            ("jane", "first"),
        ],
    )
    def test_matches_against_a_known_name(self, local: str, expected: str) -> None:
        """With a reference name, detection is evidence-based, not guesswork."""
        assert detect_pattern(local, "jane", "doe") == expected

    def test_returns_empty_when_nothing_matches(self) -> None:
        assert detect_pattern("xyz123", "jane", "doe") == ""


class TestPatternApplication:
    @pytest.mark.parametrize(
        ("pattern", "expected"),
        [
            ("first.last", "jane.doe@example.org"),
            ("firstlast", "janedoe@example.org"),
            ("f.last", "j.doe@example.org"),
            ("flast", "jdoe@example.org"),
            ("first", "jane@example.org"),
        ],
    )
    def test_renders_each_known_pattern(self, pattern: str, expected: str) -> None:
        assert apply_pattern(pattern, "jane", "doe", "example.org") == expected

    def test_unknown_pattern_yields_empty(self) -> None:
        assert apply_pattern("nonsense", "jane", "doe", "example.org") == ""

    def test_incomplete_input_yields_empty(self) -> None:
        assert apply_pattern("first.last", "jane", "", "example.org") == ""


class TestInference:
    def test_infers_from_a_colleague_address(self) -> None:
        result = infer_from_observed("Jane Doe", "example.org", ["bob.smith@example.org"])

        assert result == "jane.doe@example.org"

    def test_ignores_addresses_on_other_domains(self) -> None:
        result = infer_from_observed("Jane Doe", "example.org", ["bob.smith@other.net"])

        assert result == ""

    def test_returns_empty_without_observed_addresses(self) -> None:
        assert infer_from_observed("Jane Doe", "example.org", []) == ""

    def test_returns_empty_for_a_mononym(self) -> None:
        assert infer_from_observed("Cher", "example.org", ["a.b@example.org"]) == ""


class TestCandidateGeneration:
    def test_generates_ranked_candidates(self) -> None:
        candidates = generate_candidates("Jane Doe", "example.org")

        assert candidates[0] == "jane.doe@example.org"
        assert "jdoe@example.org" in candidates

    def test_appends_role_addresses_last(self) -> None:
        candidates = generate_candidates("Jane Doe", "example.org")

        assert candidates[-1].startswith(("contact@", "info@", "hello@"))

    def test_deduplicates(self) -> None:
        candidates = generate_candidates("Jane Doe", "example.org")

        assert len(candidates) == len(set(candidates))

    def test_no_domain_yields_nothing(self) -> None:
        assert generate_candidates("Jane Doe", "") == []

    def test_mononym_still_offers_role_addresses(self) -> None:
        candidates = generate_candidates("Cher", "example.org")

        assert candidates == ["contact@example.org", "info@example.org", "hello@example.org"]


class TestSmtpVerification:
    def test_disabled_verification_makes_no_connection(self) -> None:
        """The no_smtp fixture would fail this test if a socket were opened."""
        result = verify_email("jane@example.org", enabled=False)

        assert result.checked is False
        assert result.confirmed is False

    def test_malformed_address_is_rejected_without_a_lookup(self) -> None:
        assert verify_email("not-an-address").checked is False

    def test_missing_mx_records_means_unchecked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("prospectiq.enrichment.smtp_verify.resolve_mx", lambda _d: "")

        result = verify_email("jane@nonexistent.invalid")

        assert result.checked is False
        assert "no MX records" in result.detail

    def test_unconfirmed_is_not_the_same_as_invalid(self) -> None:
        """An unchecked result must never be presented as a negative verdict."""
        result = VerificationResult()

        assert result.confirmed is False
        assert result.checked is False
