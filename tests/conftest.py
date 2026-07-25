"""Shared pytest fixtures.

Every fixture here keeps tests hermetic: no live network calls, no dependence on
the developer's environment variables, and no writes outside ``tmp_path``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from prospectiq.config import Config
from prospectiq.models import Lead

#: Environment variables that would leak the developer's real configuration
#: into a test run.
_MANAGED_PREFIXES = ("PROSPECTIQ_", "SCOUT_")
_MANAGED_NAMES = ("LINKEDIN_COOKIE", "HUNTER_API_KEY", "NO_COLOR")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all ProspectIQ-related environment variables before each test."""
    for key in list(os.environ):
        if key.startswith(_MANAGED_PREFIXES) or key in _MANAGED_NAMES:
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make request pacing instantaneous so tests do not wait."""
    monkeypatch.setattr("prospectiq.utilities.net.time.sleep", lambda _seconds: None)


@pytest.fixture(autouse=True)
def no_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail closed on SMTP: no test may open a real mail connection.

    Tests that exercise verification patch it explicitly.
    """

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("A test attempted a real SMTP connection")

    monkeypatch.setattr("smtplib.SMTP", _blocked)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """A default configuration writing to an isolated temp directory."""
    return Config(output_dir=tmp_path / "exports", smtp_verify=False)


@pytest.fixture
def raw_github_profile() -> dict[str, Any]:
    """A representative raw GitHub API record."""
    return {
        "platform": "github",
        "username": "testuser",
        "full_name": "Test User",
        "bio": "Founder at Example Corp. reach me: test@example.org",
        "company": "Example Corp",
        "location": "Charlotte, NC",
        "website": "https://example.org",
        "follower_count": 1500,
        "following_count": 42,
        "profile_url": "https://github.com/testuser",
        "public_repos": 12,
    }


@pytest.fixture
def sample_lead() -> Lead:
    """A normalized lead with contact details already populated."""
    return Lead(
        source="github",
        username="testuser",
        display_name="Test User",
        biography="Founder at Example Corp",
        website="https://example.org",
        email="test@example.org",
        email_confidence=90,
        email_source="bio",
        phone="+15555550123",
        follower_count=8_000,
        collected_at="2026-01-01T00:00:00+00:00",
    )


class FakeResponse:
    """A minimal stand-in for a ``requests``/``httpx`` response."""

    def __init__(
        self,
        status_code: int = 200,
        text: str = "",
        json_data: Any = None,
        headers: dict[str, str] | None = None,
        url: str = "https://example.org/",
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._json = json_data
        self.headers = headers or {}
        self.url = url

    def json(self) -> Any:
        """Return the decoded payload, mimicking a JSON decode failure."""
        if self._json is None:
            raise ValueError("No JSON payload")
        return self._json

    def raise_for_status(self) -> None:
        """No-op; ProspectIQ checks status codes explicitly."""


@pytest.fixture
def fake_response() -> type[FakeResponse]:
    """Expose :class:`FakeResponse` to tests."""
    return FakeResponse


@pytest.fixture
def block_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail any test that attempts a real HTTP request."""

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("A test attempted a real network request")

    monkeypatch.setattr("requests.get", _blocked)
    monkeypatch.setattr("requests.post", _blocked)
    monkeypatch.setattr("httpx.Client.get", _blocked)
    yield
