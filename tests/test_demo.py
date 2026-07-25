"""Demo mode: it must stay offline, credential-free, and obviously fictional."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from prospectiq.branding import build_console
from prospectiq.cli import EXIT_OK, main
from prospectiq.config import Config
from prospectiq.constants import CSV_CORE_FIELDS
from prospectiq.demo import DEMO_RAW_PROFILES, build_demo_leads, run_demo


class TestDemoData:
    def test_produces_leads(self) -> None:
        assert len(build_demo_leads()) == len(DEMO_RAW_PROFILES)

    def test_covers_several_sources(self) -> None:
        sources = {lead.source for lead in build_demo_leads()}

        assert len(sources) >= 4

    def test_every_domain_is_reserved_for_documentation(self) -> None:
        """RFC 2606 reserves example.com/.org/.net so these can never resolve."""
        for lead in build_demo_leads():
            for value in (lead.email, lead.website, lead.company_domain):
                if value:
                    assert "example.com" in value or "example.org" in value

    def test_no_real_phone_numbers(self) -> None:
        """555-01xx is the reserved fictional range."""
        for lead in build_demo_leads():
            if lead.phone:
                assert "555-01" in lead.phone

    def test_leads_are_scored(self) -> None:
        leads = build_demo_leads()

        assert all(0 <= lead.lead_score <= 100 for lead in leads)
        assert any(lead.lead_score > 0 for lead in leads)

    def test_demonstrates_multiple_email_sources(self) -> None:
        sources = {lead.email_source for lead in build_demo_leads() if lead.email}

        assert len(sources) >= 3

    def test_includes_a_lead_without_contact_details(self) -> None:
        """A realistic run does not find an email for everyone."""
        assert any(not lead.email for lead in build_demo_leads())

    def test_catch_all_result_is_not_reported_as_verified(self) -> None:
        morgan = next(lead for lead in build_demo_leads() if lead.username == "themorganco")

        assert morgan.email_verified is False


class TestDemoRun:
    def test_writes_a_csv(self, tmp_path: Path) -> None:
        path = run_demo(build_console(quiet=True), tmp_path)

        assert path.exists()

    def test_csv_uses_the_documented_schema(self, tmp_path: Path) -> None:
        path = run_demo(build_console(quiet=True), tmp_path)

        with path.open(encoding="utf-8-sig", newline="") as handle:
            headers = next(csv.reader(handle))

        assert headers[: len(CSV_CORE_FIELDS)] == list(CSV_CORE_FIELDS)

    def test_csv_contains_every_demo_lead(self, tmp_path: Path) -> None:
        path = run_demo(build_console(quiet=True), tmp_path)

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        assert len(rows) == len(DEMO_RAW_PROFILES)

    def test_makes_no_network_requests(self, tmp_path: Path, block_network: None) -> None:
        """block_network turns any HTTP call into a test failure."""
        run_demo(build_console(quiet=True), tmp_path)

    def test_takes_no_configuration(self, tmp_path: Path) -> None:
        """Demo output must not depend on the user's environment at all."""
        import inspect

        parameters = set(inspect.signature(run_demo).parameters)

        assert parameters == {"console", "output_dir"}


class TestDemoCli:
    def test_demo_flag_exits_successfully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        assert main(["--demo"]) == EXIT_OK

    def test_demo_subcommand_exits_successfully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        assert main(["demo"]) == EXIT_OK

    def test_demo_creates_output_in_the_working_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        main(["--demo"])

        assert list((tmp_path / "demo_output").glob("*.csv"))

    def test_demo_respects_no_color(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        assert main(["--demo", "--no-color"]) == EXIT_OK


class TestBranding:
    def test_no_color_env_disables_color(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NO_COLOR", "1")
        from prospectiq.config import load_config

        console = build_console(load_config(load_env_file=False))

        assert console.no_color is True

    def test_color_enabled_by_default(self) -> None:
        assert build_console(Config()).no_color is False
