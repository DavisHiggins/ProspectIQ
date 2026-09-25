"""Validate local links, anchors, and asset budgets in the ProspectIQ README."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
MAX_BYTES = {
    "prospectiq-readme-hero.png": 1_500_000,
    "prospectiq-pipeline.gif": 3_000_000,
    "prospectiq-demo.gif": 4_000_000,
}
EXPECTED_DIMENSIONS = {
    "prospectiq-social-preview.png": (1280, 640),
}


def slugify(heading: str) -> str:
    """Approximate GitHub's heading-anchor algorithm for unique headings."""
    heading = re.sub(r"<[^>]+>", "", heading).strip().lower()
    heading = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE)
    return re.sub(r"\s+", "-", heading)


def main() -> int:
    text = README.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE)
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for heading in headings:
        base = slugify(heading)
        index = counts.get(base, 0)
        counts[base] = index + 1
        anchors.add(base if index == 0 else f"{base}-{index}")

    destinations = re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", text)
    destinations += re.findall(r"""(?:src|href)=["']([^"']+)["']""", text)
    destinations += re.findall(r"""srcset=["']([^"']+)["']""", text)
    for raw in destinations:
        destination = raw.strip().split(maxsplit=1)[0].strip("<>")
        if destination.startswith(("http://", "https://", "mailto:")):
            continue
        if destination.startswith("#"):
            anchor = unquote(destination[1:]).lower()
            if anchor not in anchors:
                errors.append(f"missing anchor: {destination}")
            continue
        path_part = unquote(urlsplit(destination).path)
        if not path_part:
            continue
        candidate = (ROOT / path_part).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"path escapes repository: {destination}")
            continue
        if not candidate.exists():
            errors.append(f"missing local target: {destination}")

    used_assets = {
        Path(unquote(urlsplit(item).path)).name for item in destinations if "docs/assets/" in item
    }
    for name in used_assets:
        path = ROOT / "docs" / "assets" / name
        if not path.is_file():
            continue
        limit = MAX_BYTES.get(name)
        if limit and path.stat().st_size > limit:
            errors.append(f"asset exceeds budget: {name} ({path.stat().st_size:,} > {limit:,})")
        if path.suffix.lower() in {".png", ".gif", ".jpg", ".jpeg"}:
            with Image.open(path) as image:
                expected = EXPECTED_DIMENSIONS.get(name)
                if expected and image.size != expected:
                    errors.append(f"wrong dimensions: {name} is {image.size}, expected {expected}")

    for required in (
        "prospectiq-logo-source.png",
        "prospectiq-cover.png",
        "prospectiq-logo-dark.png",
    ):
        if not (ROOT / "docs" / "assets" / required).is_file():
            warnings.append(f"canonical source unavailable: docs/assets/{required}")

    duplicate_headings = [heading for heading, count in counts.items() if count > 1]
    if duplicate_headings:
        warnings.append("duplicate heading slugs: " + ", ".join(sorted(duplicate_headings)))

    print(f"README headings: {len(headings)}")
    print(f"README destinations: {len(destinations)}")
    print(f"README assets referenced: {len(used_assets)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
