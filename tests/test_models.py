"""Lead normalization: the contract that makes sources interchangeable."""

from __future__ import annotations

from typing import Any

import pytest

from prospectiq.constants import CSV_CORE_FIELDS
from prospectiq.models import Lead


class TestNormalization:
    def test_maps_aliased_keys_to_the_core_schema(self, raw_github_profile: dict[str, Any]) -> None:
        lead = Lead.from_raw(raw_github_profile)

        assert lead.source == "github"
        assert lead.display_name == "Test User"
        assert lead.biography.startswith("Founder at Example Corp")

    def test_preserves_source_specific_fields_as_extras(
        self, raw_github_profile: dict[str, Any]
    ) -> None:
        lead = Lead.from_raw(raw_github_profile)

        assert lead.extra["public_repos"] == 12
        assert "public_repos" not in Lead.core_field_names()

    def test_source_argument_fills_in_a_missing_platform(self) -> None:
        lead = Lead.from_raw({"username": "someone"}, source="twitch")

        assert lead.source == "twitch"

    def test_raises_without_any_source(self) -> None:
        with pytest.raises(ValueError, match="without a source"):
            Lead.from_raw({"username": "someone"})

    def test_raises_without_a_username(self) -> None:
        with pytest.raises(ValueError, match="without a username"):
            Lead.from_raw({"platform": "github"})

    def test_sets_a_collection_timestamp(self) -> None:
        lead = Lead.from_raw({"platform": "github", "username": "x"})

        assert lead.collected_at.endswith("+00:00")

    def test_drops_noise_keys(self) -> None:
        lead = Lead.from_raw({"platform": "github", "username": "x", "possible_emails": ["a@b.co"]})

        assert "possible_emails" not in lead.extra


class TestTypeCoercion:
    @pytest.mark.parametrize(
        ("raw_value", "expected"), [("1500", 1500), (1500, 1500), (None, 0), ("", 0), (12.9, 12)]
    )
    def test_counts_coerce_to_int(self, raw_value: Any, expected: int) -> None:
        lead = Lead.from_raw({"platform": "github", "username": "x", "follower_count": raw_value})

        assert lead.follower_count == expected

    def test_malformed_count_does_not_raise(self) -> None:
        lead = Lead.from_raw({"platform": "github", "username": "x", "follower_count": "many"})

        assert lead.follower_count == 0

    def test_none_text_fields_become_empty_strings(self) -> None:
        lead = Lead.from_raw({"platform": "github", "username": "x", "bio": None})

        assert lead.biography == ""


class TestCrossSourceConsistency:
    """Different sources must produce identically shaped leads."""

    RAW_BY_SOURCE: dict[str, dict[str, Any]] = {
        "instagram": {
            "platform": "instagram",
            "username": "a",
            "full_name": "A",
            "bio": "b",
            "follower_count": 10,
            "post_count": 3,
        },
        "linkedin": {
            "platform": "linkedin",
            "username": "b",
            "full_name": "B",
            "headline": "CEO at X",
            "bio": "c",
        },
        "youtube": {
            "platform": "youtube",
            "username": "c",
            "full_name": "C",
            "subscriber_count": 900,
            "links": ["https://example.org"],
        },
        "twitch": {
            "platform": "twitch",
            "username": "d",
            "full_name": "D",
            "is_partner": True,
            "follower_count": 50,
        },
    }

    @pytest.mark.parametrize("source", list(RAW_BY_SOURCE))
    def test_every_source_yields_the_same_core_fields(self, source: str) -> None:
        lead = Lead.from_raw(self.RAW_BY_SOURCE[source])
        row = lead.to_dict()

        for field in CSV_CORE_FIELDS:
            assert field in row, f"{source} lead is missing {field}"

    def test_subscriber_count_normalizes_to_follower_count(self) -> None:
        lead = Lead.from_raw(self.RAW_BY_SOURCE["youtube"])

        assert lead.follower_count == 900


class TestExportShape:
    def test_to_dict_starts_with_the_documented_core_fields(self, sample_lead: Lead) -> None:
        keys = list(sample_lead.to_dict())

        assert keys[: len(CSV_CORE_FIELDS)] == list(CSV_CORE_FIELDS)

    def test_flattens_list_extras_into_one_cell(self) -> None:
        lead = Lead.from_raw(
            {
                "platform": "youtube",
                "username": "x",
                "links": ["https://a.example", "https://b.example"],
            }
        )

        assert lead.to_dict()["links"] == "https://a.example; https://b.example"

    def test_extras_can_be_excluded(self, raw_github_profile: dict[str, Any]) -> None:
        lead = Lead.from_raw(raw_github_profile)

        assert "public_repos" not in lead.to_dict(flatten_extra=False)

    def test_has_contact_reflects_email_or_phone(self, sample_lead: Lead) -> None:
        assert sample_lead.has_contact is True
        assert Lead(source="github", username="x").has_contact is False
