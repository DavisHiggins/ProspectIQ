"""CSV export.

Exports use a stable column order so downstream spreadsheets and CRM imports do
not break between runs: the documented core schema first, then any extra fields
a source provided, sorted alphabetically.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from prospectiq.constants import CSV_CORE_FIELDS, EXPORT_PREFIX
from prospectiq.logging_config import get_logger
from prospectiq.models import Lead
from prospectiq.utilities.errors import ExportError

logger = get_logger(__name__)

#: Characters that a spreadsheet may interpret as the start of a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_component(value: str) -> str:
    """Reduce a user-supplied string to a safe filename component."""
    cleaned = _UNSAFE_FILENAME.sub("_", value.strip()).strip("._")
    return cleaned or "export"


def build_export_path(
    output_dir: Path, source: str = "", timestamp: datetime | None = None
) -> Path:
    """Build the path for a new export file.

    Args:
        output_dir: Directory the file belongs in.
        source: Optional source name included in the filename.
        timestamp: Defaults to now.

    Returns:
        An absolute path of the form
        ``<output_dir>/prospectiq_leads_<source>_<YYYYmmdd_HHMMSS>.csv``.
    """
    stamp = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")
    parts = [EXPORT_PREFIX]
    if source:
        parts.append(_sanitize_component(source))
    parts.append(stamp)
    return (output_dir / f"{'_'.join(parts)}.csv").resolve()


def _sanitize_cell(value: object) -> object:
    """Neutralize spreadsheet formula injection in exported text.

    Scraped bios are attacker-controlled text. A cell starting with ``=`` is
    executed as a formula by Excel and Sheets, so such values are prefixed with
    an apostrophe to force literal interpretation.
    """
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def build_fieldnames(leads: list[Lead]) -> list[str]:
    """Return the column order for a set of leads."""
    extras: set[str] = set()
    for lead in leads:
        extras.update(key for key in lead.to_dict() if key not in CSV_CORE_FIELDS)
    return list(CSV_CORE_FIELDS) + sorted(extras)


def export_leads(
    leads: list[Lead],
    output_dir: Path,
    *,
    source: str = "",
    path: Path | None = None,
) -> Path:
    """Write leads to a CSV file.

    Args:
        leads: The leads to export. Must not be empty.
        output_dir: Directory to write into; created if absent.
        source: Optional source name for the generated filename.
        path: Explicit output path, overriding ``output_dir`` and ``source``.

    Returns:
        The path written.

    Raises:
        ExportError: The list is empty or the file could not be written.
    """
    if not leads:
        raise ExportError("Nothing to export: no leads were collected.")

    target = path.resolve() if path else build_export_path(output_dir, source)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExportError(f"Could not create export directory {target.parent}: {exc}") from exc

    fieldnames = build_fieldnames(leads)

    try:
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for lead in leads:
                row = {key: _sanitize_cell(value) for key, value in lead.to_dict().items()}
                writer.writerow(row)
    except OSError as exc:
        raise ExportError(f"Could not write {target}: {exc}") from exc

    logger.info("Exported %d leads to %s", len(leads), target)
    return target


def list_exports(output_dir: Path, limit: int = 10) -> list[Path]:
    """Return existing export files, newest first."""
    if not output_dir.is_dir():
        return []
    files = sorted(
        output_dir.glob(f"{EXPORT_PREFIX}_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[:limit]
