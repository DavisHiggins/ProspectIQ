"""CLI argument handling, input parsing, and error paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from prospectiq import __version__
from prospectiq.cli import EXIT_ERROR, EXIT_OK, build_parser, main, read_identifiers
from prospectiq.updates import check_for_update, is_newer, parse_version
from prospectiq.utilities.errors import ConfigurationError


class TestHelpAndVersion:
    def test_version_flag_prints_the_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exit_info:
            main(["--version"])

        assert exit_info.value.code == EXIT_OK
        assert __version__ in capsys.readouterr().out

    def test_version_matches_the_package(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["--version"])

        assert capsys.readouterr().out.strip() == f"ProspectIQ {__version__}"

    def test_help_flag_lists_commands(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exit_info:
            main(["--help"])

        output = capsys.readouterr().out
        assert exit_info.value.code == EXIT_OK
        for command in ("collect", "sources", "exports", "demo"):
            assert command in output

    def test_help_advertises_demo_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["--help"])

        assert "--demo" in capsys.readouterr().out

    def test_help_mentions_no_color(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["--help"])

        assert "--no-color" in capsys.readouterr().out


class TestParser:
    def test_collect_requires_a_source(self) -> None:
        parser = build_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["collect"])

    def test_collect_rejects_an_unknown_source(self) -> None:
        parser = build_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["collect", "--source", "myspace"])

    def test_usernames_accumulate(self) -> None:
        args = build_parser().parse_args(["collect", "-s", "github", "-u", "one", "-u", "two"])

        assert args.username == ["one", "two"]

    def test_defaults_to_no_subcommand(self) -> None:
        assert build_parser().parse_args([]).command is None


class TestCommands:
    def test_sources_command_succeeds(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["sources"]) == EXIT_OK
        assert "instagram" in capsys.readouterr().out

    def test_exports_command_handles_an_empty_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROSPECTIQ_OUTPUT_DIR", str(tmp_path))

        assert main(["exports"]) == EXIT_OK

    def test_collect_without_usernames_fails_cleanly(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["collect", "--source", "github"])

        assert exit_code == EXIT_ERROR
        assert "No usernames" in capsys.readouterr().out

    def test_collect_reports_a_missing_input_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["collect", "--source", "github", "--input", str(tmp_path / "absent.txt")])

        assert exit_code == EXIT_ERROR
        assert "not found" in capsys.readouterr().out

    def test_deprecated_variable_warns_but_still_runs(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("SCOUT_PROXY", "http://legacy.example.com:8080")

        exit_code = main(["sources"])

        assert exit_code == EXIT_OK
        assert "deprecated" in capsys.readouterr().out


class TestIdentifierInput:
    def test_reads_a_text_file(self, tmp_path: Path) -> None:
        path = tmp_path / "users.txt"
        path.write_text("alice\n@bob\n\n  carol  \n", encoding="utf-8")

        assert read_identifiers(path) == ["alice", "bob", "carol"]

    def test_reads_a_csv_with_a_username_column(self, tmp_path: Path) -> None:
        path = tmp_path / "users.csv"
        path.write_text("name,username\nAlice,alice\nBob,@bob\n", encoding="utf-8")

        assert read_identifiers(path) == ["alice", "bob"]

    def test_falls_back_to_the_first_csv_column(self, tmp_path: Path) -> None:
        path = tmp_path / "users.csv"
        path.write_text("handle_col\nalice\nbob\n", encoding="utf-8")

        assert read_identifiers(path) == ["alice", "bob"]

    def test_missing_file_raises_a_configuration_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError, match="not found"):
            read_identifiers(tmp_path / "absent.txt")

    def test_empty_file_yields_no_identifiers(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.txt"
        path.write_text("", encoding="utf-8")

        assert read_identifiers(path) == []


class TestUpdateChecker:
    def test_disabled_by_default_makes_no_request(self) -> None:
        """The no-network guarantee: an opt-in check must not fire."""
        assert check_for_update(enabled=False) is None

    @pytest.mark.parametrize(
        ("raw", "expected"), [("1.2.3", (1, 2, 3)), ("v0.1.0", (0, 1, 0)), ("2.0", (2, 0))]
    )
    def test_parses_versions(self, raw: str, expected: tuple[int, ...]) -> None:
        assert parse_version(raw) == expected

    def test_unparseable_version_sorts_lowest(self) -> None:
        assert parse_version("garbage") == (0,)

    @pytest.mark.parametrize(
        ("candidate", "current", "expected"),
        [("0.2.0", "0.1.0", True), ("0.1.0", "0.1.0", False), ("0.0.9", "0.1.0", False)],
    )
    def test_compares_versions(self, candidate: str, current: str, expected: bool) -> None:
        assert is_newer(candidate, current) is expected
