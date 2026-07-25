"""Configuration loading, including the deprecated SCOUT_ fallback."""

from __future__ import annotations

from pathlib import Path

import pytest

from prospectiq.config import Config, get_deprecation_warnings, load_config, load_dotenv
from prospectiq.constants import DEFAULT_DELAY_MAX, DEFAULT_DELAY_MIN, MIN_ALLOWED_DELAY


class TestDefaults:
    def test_loads_with_no_environment_set(self) -> None:
        config = load_config(load_env_file=False)

        assert config.proxy_url == ""
        assert config.proxy_file is None
        assert config.use_free_proxy is False
        assert config.delay_min == DEFAULT_DELAY_MIN
        assert config.delay_max == DEFAULT_DELAY_MAX
        assert config.smtp_verify is True

    def test_update_check_is_opt_in(self) -> None:
        """No outbound request should happen unless explicitly enabled."""
        assert load_config(load_env_file=False).update_check is False

    def test_proxy_mode_reports_none(self) -> None:
        assert load_config(load_env_file=False).proxy_mode == "none"


class TestCurrentVariables:
    def test_reads_prospectiq_proxy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROSPECTIQ_PROXY", "http://proxy.example.com:8080")

        config = load_config(load_env_file=False)

        assert config.proxy_url == "http://proxy.example.com:8080"
        assert config.proxy_mode == "custom"
        assert get_deprecation_warnings() == []

    @pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE"])
    def test_boolean_parsing_accepts_common_spellings(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("PROSPECTIQ_FREE_PROXY", value)

        assert load_config(load_env_file=False).use_free_proxy is True

    @pytest.mark.parametrize("value", ["false", "0", "no", ""])
    def test_boolean_parsing_rejects_falsey_spellings(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("PROSPECTIQ_FREE_PROXY", value)

        assert load_config(load_env_file=False).use_free_proxy is False

    def test_reads_delays(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROSPECTIQ_DELAY_MIN", "3.5")
        monkeypatch.setenv("PROSPECTIQ_DELAY_MAX", "7.0")

        config = load_config(load_env_file=False)

        assert config.delay_min == 3.5
        assert config.delay_max == 7.0
        assert config.delay_explicitly_set is True


class TestDeprecatedFallback:
    def test_scout_proxy_is_honoured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SCOUT_PROXY", "http://legacy.example.com:8080")

        config = load_config(load_env_file=False)

        assert config.proxy_url == "http://legacy.example.com:8080"

    def test_scout_proxy_emits_a_deprecation_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SCOUT_PROXY", "http://legacy.example.com:8080")

        load_config(load_env_file=False)
        warnings = get_deprecation_warnings()

        assert len(warnings) == 1
        assert "SCOUT_PROXY is deprecated" in warnings[0]
        assert "PROSPECTIQ_PROXY" in warnings[0]

    def test_deprecation_is_non_blocking(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A legacy variable must warn, not raise."""
        monkeypatch.setenv("SCOUT_DELAY_MIN", "4.0")

        config = load_config(load_env_file=False)

        assert config.delay_min == 4.0

    def test_new_variable_wins_over_legacy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROSPECTIQ_PROXY", "http://new.example.com:1234")
        monkeypatch.setenv("SCOUT_PROXY", "http://old.example.com:8080")

        config = load_config(load_env_file=False)

        assert config.proxy_url == "http://new.example.com:1234"
        assert get_deprecation_warnings() == []

    @pytest.mark.parametrize(
        "name", ["PROXY", "PROXY_FILE", "FREE_PROXY", "DELAY_MIN", "DELAY_MAX"]
    )
    def test_every_documented_alias_is_supported(
        self, monkeypatch: pytest.MonkeyPatch, name: str, tmp_path: Path
    ) -> None:
        value = str(tmp_path / "p.txt") if name == "PROXY_FILE" else "2.0"
        if name == "PROXY_FILE":
            (tmp_path / "p.txt").write_text("http://x.example.com:1", encoding="utf-8")

        monkeypatch.setenv(f"SCOUT_{name}", value)
        load_config(load_env_file=False)

        assert any(f"SCOUT_{name}" in w for w in get_deprecation_warnings())

    def test_scout_linkedin_cookie_is_not_silently_accepted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only the documented aliases fall back; others must not."""
        monkeypatch.setenv("SCOUT_LINKEDIN_COOKIE", "x" * 60)

        assert load_config(load_env_file=False).linkedin_cookie == ""


class TestVendorAliases:
    def test_unprefixed_linkedin_cookie_is_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINKEDIN_COOKIE", "a" * 60)

        config = load_config(load_env_file=False)

        assert config.has_linkedin_cookie() is True
        assert get_deprecation_warnings() == []

    def test_prefixed_cookie_takes_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINKEDIN_COOKIE", "old")
        monkeypatch.setenv("PROSPECTIQ_LINKEDIN_COOKIE", "new")

        assert load_config(load_env_file=False).linkedin_cookie == "new"


class TestValidation:
    def test_unparseable_delay_falls_back_with_a_warning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROSPECTIQ_DELAY_MIN", "not-a-number")

        config = load_config(load_env_file=False)

        assert config.delay_min == DEFAULT_DELAY_MIN
        assert any("not a number" in w for w in get_deprecation_warnings())

    def test_delay_floor_is_enforced(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Users cannot configure an abusive request rate."""
        monkeypatch.setenv("PROSPECTIQ_DELAY_MIN", "0")

        assert load_config(load_env_file=False).delay_min == MIN_ALLOWED_DELAY

    def test_inverted_delay_range_is_corrected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROSPECTIQ_DELAY_MIN", "9.0")
        monkeypatch.setenv("PROSPECTIQ_DELAY_MAX", "2.0")

        config = load_config(load_env_file=False)

        assert config.delay_max >= config.delay_min
        assert any("below delay min" in w for w in get_deprecation_warnings())

    def test_missing_proxy_file_warns_and_is_ignored(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("PROSPECTIQ_PROXY_FILE", str(tmp_path / "absent.txt"))

        config = load_config(load_env_file=False)

        assert config.proxy_file is None
        assert any("Proxy file not found" in w for w in get_deprecation_warnings())


class TestDotenv:
    def test_reads_key_value_pairs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# a comment\nPROSPECTIQ_PROXY=http://from-file.example.com\n\n",
            encoding="utf-8",
        )

        load_dotenv(env_file)
        config = load_config(load_env_file=False)

        assert config.proxy_url == "http://from-file.example.com"

    def test_environment_wins_over_dotenv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("PROSPECTIQ_PROXY=http://from-file.example.com", encoding="utf-8")
        monkeypatch.setenv("PROSPECTIQ_PROXY", "http://from-shell.example.com")

        load_dotenv(env_file)

        assert load_config(load_env_file=False).proxy_url == "http://from-shell.example.com"

    def test_missing_file_is_not_an_error(self, tmp_path: Path) -> None:
        load_dotenv(tmp_path / "nope.env")

    def test_strips_surrounding_quotes(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text('PROSPECTIQ_PROXY="http://quoted.example.com"', encoding="utf-8")

        load_dotenv(env_file)

        assert load_config(load_env_file=False).proxy_url == "http://quoted.example.com"


class TestSourceDelays:
    def test_per_source_defaults_apply_when_unset(self) -> None:
        config = load_config(load_env_file=False)

        assert config.delay_for("linkedin") == (4.0, 8.0)
        assert config.delay_for("github") == (1.0, 2.0)

    def test_explicit_setting_overrides_per_source_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROSPECTIQ_DELAY_MIN", "10")
        monkeypatch.setenv("PROSPECTIQ_DELAY_MAX", "12")

        config = load_config(load_env_file=False)

        assert config.delay_for("github") == (10.0, 12.0)

    def test_unknown_source_falls_back_to_global_delay(self) -> None:
        config = Config(delay_min=1.5, delay_max=3.0)

        assert config.delay_for("unknown-source") == (1.5, 3.0)
