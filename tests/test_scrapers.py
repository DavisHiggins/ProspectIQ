"""Scraper behaviour with mocked HTTP. No test here touches the network."""

from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from prospectiq.config import Config
from prospectiq.scrapers import (
    SOURCES,
    collect,
    get_source,
    github,
    instagram,
    source_keys,
    tiktok,
    twitch,
)
from prospectiq.scrapers.base import looks_blocked, raise_for_status
from prospectiq.utilities.errors import (
    AuthenticationError,
    BlockedError,
    ConfigurationError,
    NotFoundError,
    RateLimitedError,
    ScraperError,
)

pytestmark = pytest.mark.usefixtures("clean_env")


class TestStatusMapping:
    """One place decides what each HTTP status means for every source."""

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (404, NotFoundError),
            (429, RateLimitedError),
            (401, AuthenticationError),
            (403, BlockedError),
            (500, ScraperError),
        ],
    )
    def test_status_codes_map_to_typed_errors(self, status: int, expected: type[Exception]) -> None:
        with pytest.raises(expected):
            raise_for_status(status, source="test", target="x")

    @pytest.mark.parametrize("status", [200, 201, 204])
    def test_success_codes_do_not_raise(self, status: int) -> None:
        raise_for_status(status, source="test", target="x")

    def test_rate_limit_message_suggests_slowing_down(self) -> None:
        with pytest.raises(RateLimitedError, match="PROSPECTIQ_DELAY_MIN"):
            raise_for_status(429, source="test", target="x")

    @pytest.mark.parametrize(
        "html", ["<p>Please complete the CAPTCHA</p>", "We detected unusual traffic"]
    )
    def test_challenge_pages_are_detected(self, html: str) -> None:
        assert looks_blocked(html) is True

    def test_ordinary_html_is_not_flagged(self) -> None:
        assert looks_blocked("<html><body>Profile page</body></html>") is False


class TestRegistry:
    def test_every_source_is_registered(self) -> None:
        assert set(source_keys()) == {
            "instagram",
            "tiktok",
            "linkedin",
            "github",
            "youtube",
            "twitch",
            "linkbio",
            "pinterest",
        }

    def test_unknown_source_raises(self) -> None:
        with pytest.raises(ConfigurationError, match="Unknown source"):
            get_source("myspace")

    def test_only_linkedin_requires_auth(self) -> None:
        needing_auth = {key for key, src in SOURCES.items() if src.requires_auth}

        assert needing_auth == {"linkedin"}

    def test_linkedin_is_unavailable_without_a_cookie(self) -> None:
        available, reason = SOURCES["linkedin"].is_available(Config())

        assert available is False
        assert "PROSPECTIQ_LINKEDIN_COOKIE" in reason

    def test_linkedin_is_available_with_a_cookie(self) -> None:
        available, _ = SOURCES["linkedin"].is_available(Config(linkedin_cookie="x" * 60))

        assert available is True

    def test_collect_refuses_unavailable_sources(self, config: Config) -> None:
        with pytest.raises(ConfigurationError, match="unavailable"):
            collect("linkedin", "someone", config)


class TestGitHubScraper:
    PAYLOAD: dict[str, Any] = {
        "login": "testuser",
        "name": "Test User",
        "bio": "Founder at Example Corp",
        "email": "test@example.org",
        "company": "@ExampleCorp",
        "location": "Charlotte, NC",
        "blog": "https://example.org",
        "followers": 1500,
        "following": 42,
        "public_repos": 12,
        "html_url": "https://github.com/testuser",
        "hireable": True,
    }

    def test_parses_a_profile(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(
            requests, "get", lambda *a, **k: fake_response(200, json_data=self.PAYLOAD)
        )

        record = github.fetch("testuser", config)

        assert record is not None
        assert record["username"] == "testuser"
        assert record["email"] == "test@example.org"
        assert record["follower_count"] == 1500

    def test_strips_the_at_prefix_from_company(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(
            requests, "get", lambda *a, **k: fake_response(200, json_data=self.PAYLOAD)
        )

        record = github.fetch("testuser", config)

        assert record is not None
        assert record["company"] == "ExampleCorp"

    def test_empty_profile_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(
            requests,
            "get",
            lambda *a, **k: fake_response(200, json_data={"login": "ghost", "followers": 0}),
        )

        assert github.fetch("ghost", config) is None

    def test_missing_user_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(requests, "get", lambda *a, **k: fake_response(404))

        with pytest.raises(NotFoundError):
            github.fetch("nobody", config)

    def test_quota_exhaustion_is_a_rate_limit_not_a_block(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        """GitHub signals quota exhaustion with 403 plus a header."""
        monkeypatch.setattr(
            requests,
            "get",
            lambda *a, **k: fake_response(403, headers={"X-RateLimit-Remaining": "0"}),
        )

        with pytest.raises(RateLimitedError, match="60 requests/hour"):
            github.fetch("testuser", config)

    def test_normalizes_into_a_lead(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(
            requests, "get", lambda *a, **k: fake_response(200, json_data=self.PAYLOAD)
        )

        lead = collect("github", "testuser", config)

        assert lead is not None
        assert lead.source == "github"
        assert lead.display_name == "Test User"
        assert lead.extra["public_repos"] == 12


class TestTwitchScraper:
    PAYLOAD: dict[str, Any] = {
        "data": {
            "user": {
                "login": "streamer",
                "displayName": "Streamer",
                "description": "Contact biz@example.org",
                "followers": {"totalCount": 50_000},
                "roles": {"isPartner": True, "isAffiliate": False},
                "channel": {"socialMedias": [{"name": "site", "url": "https://example.org"}]},
            }
        }
    }

    def test_parses_a_channel(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(
            requests, "post", lambda *a, **k: fake_response(200, json_data=self.PAYLOAD)
        )

        record = twitch.fetch("streamer", config)

        assert record is not None
        assert record["follower_count"] == 50_000
        assert record["is_partner"] is True
        assert record["email"] == "biz@example.org"

    def test_missing_channel_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(
            requests, "post", lambda *a, **k: fake_response(200, json_data={"data": {"user": None}})
        )

        with pytest.raises(NotFoundError):
            twitch.fetch("ghost", config)

    def test_graphql_errors_surface(
        self, monkeypatch: pytest.MonkeyPatch, config: Config, fake_response: Any
    ) -> None:
        monkeypatch.setattr(
            requests,
            "post",
            lambda *a, **k: fake_response(200, json_data={"errors": [{"message": "bad"}]}),
        )

        with pytest.raises(ScraperError):
            twitch.fetch("x", config)


class TestInstagramScraper:
    def build_html(self, **overrides: Any) -> str:
        """Build page markup shaped like Instagram's real embedded JSON.

        Compact separators matter: the live payload has no space after the
        colon, and the extraction patterns are written against that.
        """
        fields = {
            "username": "testuser",
            "full_name": "Test User",
            "biography": "Coach | hello@example.org",
            "follower_count": 24800,
            "following_count": 612,
            "media_count": 318,
            **overrides,
        }
        payload = json.dumps(fields, separators=(",", ":"))
        return f'<html>{payload}"is_verified":true</html>'

    def test_parses_a_profile(self, monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
        monkeypatch.setattr(
            "prospectiq.scrapers.instagram.fetch_html",
            lambda *a, **k: self.build_html(),
        )

        record = instagram.fetch("testuser", config)

        assert record is not None
        assert record["follower_count"] == 24800
        assert record["email"] == "hello@example.org"

    def test_missing_profile_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch, config: Config
    ) -> None:
        monkeypatch.setattr(
            "prospectiq.scrapers.instagram.fetch_html",
            lambda *a, **k: "<html>Sorry, this page isn't available.</html>",
        )

        with pytest.raises(NotFoundError):
            instagram.fetch("ghost", config)

    def test_failed_extraction_raises_rather_than_reporting_zero(
        self, monkeypatch: pytest.MonkeyPatch, config: Config
    ) -> None:
        """Zero followers means extraction failed, not a real count."""
        monkeypatch.setattr(
            "prospectiq.scrapers.instagram.fetch_html",
            lambda *a, **k: "<html><body>nothing useful</body></html>",
        )

        with pytest.raises(ScraperError, match="Could not extract"):
            instagram.fetch("testuser", config)

    def test_login_wall_returns_none(self, monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
        monkeypatch.setattr(
            "prospectiq.scrapers.instagram.fetch_html",
            lambda *a, **k: "<html>/accounts/login password required</html>",
        )

        assert instagram.fetch("testuser", config) is None


class TestTikTokScraper:
    def test_parses_a_profile(self, monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
        payload = {
            "__DEFAULT_SCOPE__": {
                "webapp.user-detail": {
                    "userInfo": {
                        "user": {
                            "uniqueId": "creator",
                            "nickname": "Creator",
                            "signature": "biz@example.org",
                            "verified": True,
                        },
                        "stats": {"followerCount": 90_000, "heartCount": 1_200_000},
                    }
                }
            }
        }
        html = (
            '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'
            + json.dumps(payload)
            + "</script>"
        )
        monkeypatch.setattr("prospectiq.scrapers.tiktok.fetch_html", lambda *a, **k: html)

        record = tiktok.fetch("creator", config)

        assert record is not None
        assert record["follower_count"] == 90_000
        assert record["email"] == "biz@example.org"

    def test_missing_payload_raises(self, monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
        monkeypatch.setattr(
            "prospectiq.scrapers.tiktok.fetch_html", lambda *a, **k: "<html>blocked</html>"
        )

        with pytest.raises(ScraperError):
            tiktok.fetch("creator", config)


class TestLinkedInScraper:
    def test_requires_a_cookie(self, config: Config) -> None:
        from prospectiq.scrapers import linkedin

        with pytest.raises(AuthenticationError, match="session cookie"):
            linkedin.fetch("someone", config)

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("https://www.linkedin.com/in/jane-doe/", "jane-doe"),
            ("jane-doe", "jane-doe"),
            ("@jane-doe", "jane-doe"),
            ("linkedin.com/in/jane-doe?trk=x", "jane-doe"),
        ],
    )
    def test_identifier_normalization(self, raw: str, expected: str) -> None:
        from prospectiq.scrapers.linkedin import _normalize_identifier

        assert _normalize_identifier(raw) == expected
