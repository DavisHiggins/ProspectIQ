"""CSV export: schema stability, safety, and error handling."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest

from prospectiq.constants import CSV_CORE_FIELDS, EXPORT_PREFIX
from prospectiq.exporters import build_export_path, build_fieldnames, export_leads, list_exports
from prospectiq.models import Lead
from prospectiq.utilities.errors import ExportError


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read an exported CSV back into headers and rows."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


class TestExport:
    def test_writes_a_file(self, sample_lead: Lead, tmp_path: Path) -> None:
        path = export_leads([sample_lead], tmp_path)

        assert path.exists()
        assert path.suffix == ".csv"

    def test_creates_the_output_directory(self, sample_lead: Lead, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "deeper"

        path = export_leads([sample_lead], target)

        assert path.parent == target.resolve()

    def test_writes_one_row_per_lead(self, sample_lead: Lead, tmp_path: Path) -> None:
        leads = [sample_lead, Lead(source="twitch", username="second")]

        _, rows = read_csv(export_leads(leads, tmp_path))

        assert len(rows) == 2

    def test_round_trips_values(self, sample_lead: Lead, tmp_path: Path) -> None:
        _, rows = read_csv(export_leads([sample_lead], tmp_path))

        assert rows[0]["username"] == "testuser"
        assert rows[0]["email"] == "test@example.org"
        assert rows[0]["email_confidence"] == "90"

    def test_empty_list_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ExportError, match="Nothing to export"):
            export_leads([], tmp_path)

    def test_explicit_path_is_honoured(self, sample_lead: Lead, tmp_path: Path) -> None:
        target = tmp_path / "custom.csv"

        assert export_leads([sample_lead], tmp_path, path=target) == target.resolve()


class TestSchemaStability:
    def test_core_fields_come_first_in_order(self, sample_lead: Lead, tmp_path: Path) -> None:
        headers, _ = read_csv(export_leads([sample_lead], tmp_path))

        assert headers[: len(CSV_CORE_FIELDS)] == list(CSV_CORE_FIELDS)

    def test_extra_fields_are_appended_alphabetically(self, tmp_path: Path) -> None:
        lead = Lead.from_raw(
            {"platform": "github", "username": "x", "zeta": 1, "alpha": 2, "public_repos": 3}
        )

        headers, _ = read_csv(export_leads([lead], tmp_path))
        extras = headers[len(CSV_CORE_FIELDS) :]

        assert extras == sorted(extras)
        assert extras == ["alpha", "public_repos", "zeta"]

    def test_union_of_extras_across_mixed_sources(self, tmp_path: Path) -> None:
        """Leads from different sources must share one header row."""
        leads = [
            Lead.from_raw({"platform": "github", "username": "a", "public_repos": 5}),
            Lead.from_raw({"platform": "twitch", "username": "b", "is_partner": True}),
        ]

        headers, rows = read_csv(export_leads(leads, tmp_path))

        assert "public_repos" in headers
        assert "is_partner" in headers
        assert rows[0]["is_partner"] == ""

    def test_fieldnames_helper_matches_written_header(
        self, sample_lead: Lead, tmp_path: Path
    ) -> None:
        headers, _ = read_csv(export_leads([sample_lead], tmp_path))

        assert headers == build_fieldnames([sample_lead])


class TestFormulaInjection:
    @pytest.mark.parametrize("payload", ["=1+1", "+cmd", "-2+3", "@SUM(A1)"])
    def test_formula_like_values_are_neutralized(self, payload: str, tmp_path: Path) -> None:
        """Scraped bios are untrusted; a spreadsheet must not execute them."""
        lead = Lead(source="github", username="x", biography=payload)

        _, rows = read_csv(export_leads([lead], tmp_path))

        assert rows[0]["biography"].startswith("'")

    def test_ordinary_text_is_untouched(self, tmp_path: Path) -> None:
        lead = Lead(source="github", username="x", biography="Founder at Acme")

        _, rows = read_csv(export_leads([lead], tmp_path))

        assert rows[0]["biography"] == "Founder at Acme"


class TestPaths:
    def test_filename_uses_the_project_prefix(self, tmp_path: Path) -> None:
        path = build_export_path(tmp_path, "github", datetime(2026, 3, 4, 5, 6, 7))

        assert path.name == f"{EXPORT_PREFIX}_github_20260304_050607.csv"

    def test_source_is_sanitized(self, tmp_path: Path) -> None:
        path = build_export_path(tmp_path, "../../etc/passwd")

        assert "/" not in path.name
        assert ".." not in path.name
        assert path.parent == tmp_path.resolve()

    def test_list_exports_returns_newest_first(self, sample_lead: Lead, tmp_path: Path) -> None:
        first = export_leads([sample_lead], tmp_path, path=tmp_path / f"{EXPORT_PREFIX}_a.csv")
        second = export_leads([sample_lead], tmp_path, path=tmp_path / f"{EXPORT_PREFIX}_b.csv")
        import os

        os.utime(second, (2_000_000_000, 2_000_000_000))

        assert list_exports(tmp_path)[0] == second
        assert first in list_exports(tmp_path)

    def test_list_exports_handles_a_missing_directory(self, tmp_path: Path) -> None:
        assert list_exports(tmp_path / "absent") == []
