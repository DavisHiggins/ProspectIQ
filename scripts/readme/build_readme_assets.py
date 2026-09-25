"""Build ProspectIQ README visuals from repository facts and local brand assets.

The diagrams and animations are deterministic and use no network services. When
the canonical logo and cover are available, place them at the paths documented
in ``docs/README_ASSET_SETUP.md``; this script will preserve optimized source
copies and use the cover as the hero backdrop. Without those files, it produces
an honest pipeline-led fallback hero and never invents a replacement logo.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"

MIDNIGHT = "#001019"
DEEP_NAVY = "#0E272F"
STRUCTURAL_NAVY = "#143D49"
GLASS_TEAL = "#225E6A"
TEAL = "#2999A3"
CYAN = "#9CC6CF"
GOLD = "#C9B171"
BRIGHT_GOLD = "#D6A84B"
WHITE = "#F5F8FA"
SLATE = "#8FA5B0"


def _font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    """Load a broadly available local font with a portable fallback."""
    candidates = []
    if sys.platform == "win32":
        if mono:
            candidates.extend(
                [
                    Path("C:/Windows/Fonts/CascadiaMono.ttf"),
                    Path("C:/Windows/Fonts/consola.ttf"),
                ]
            )
        else:
            candidates.append(
                Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf")
            )
    candidates.extend(
        [
            Path(
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
                if mono
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
            if bold
            else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def _svg_header(width: int, height: int, title: str, description: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(title)}</title>
  <desc id="desc">{html.escape(description)}</desc>
  <defs>
    <linearGradient id="canvas" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{MIDNIGHT}"/>
      <stop offset="1" stop-color="{DEEP_NAVY}"/>
    </linearGradient>
    <linearGradient id="flow" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{GLASS_TEAL}"/>
      <stop offset="0.52" stop-color="{TEAL}"/>
      <stop offset="1" stop-color="{GOLD}"/>
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
      <path d="M48 0H0V48" fill="none" stroke="{STRUCTURAL_NAVY}" stroke-width="1" opacity=".35"/>
    </pattern>
    <style>
      .label {{ font: 700 17px system-ui, sans-serif; letter-spacing: 2px; fill: {WHITE}; }}
      .small {{ font: 500 14px system-ui, sans-serif; fill: {SLATE}; }}
      .eyebrow {{ font: 700 13px system-ui, sans-serif; letter-spacing: 3px; fill: {GOLD}; }}
      .title {{ font: 700 28px system-ui, sans-serif; fill: {WHITE}; }}
      .card {{ fill: {DEEP_NAVY}; stroke: {GLASS_TEAL}; stroke-width: 1.5; }}
    </style>
  </defs>
  <rect width="100%" height="100%" rx="20" fill="url(#canvas)"/>
  <rect width="100%" height="100%" rx="20" fill="url(#grid)"/>
'''


def build_pipeline_svg() -> None:
    stages = ["COLLECT", "NORMALIZE", "ENRICH", "SCORE", "EXPORT"]
    width, height = 1440, 430
    svg = _svg_header(
        width,
        height,
        "ProspectIQ pipeline",
        "Public sources pass through collection, normalization, enrichment, scoring, and CSV export.",
    )
    svg += """  <text x="72" y="68" class="eyebrow">PUBLIC DATA → STRUCTURED RECORDS</text>
  <text x="72" y="108" class="title">One traceable path from source to local CSV</text>
  <path d="M170 245H1270" stroke="url(#flow)" stroke-width="4" opacity=".9"/>
"""
    centers = [185, 445, 705, 965, 1225]
    subtitles = [
        "public profiles",
        "one Lead schema",
        "contact evidence",
        "additive rules",
        "stable columns",
    ]
    for i, (x, label, subtitle) in enumerate(zip(centers, stages, subtitles, strict=True)):
        accent = GOLD if label in {"SCORE", "EXPORT"} else TEAL
        svg += f'''  <rect x="{x - 100}" y="177" width="200" height="136" rx="15" class="card"/>
  <circle cx="{x}" cy="245" r="30" fill="{MIDNIGHT}" stroke="{accent}" stroke-width="3"/>
  <circle cx="{x}" cy="245" r="7" fill="{accent}" filter="url(#glow)"/>
  <text x="{x}" y="342" text-anchor="middle" class="label">{label}</text>
  <text x="{x}" y="370" text-anchor="middle" class="small">{subtitle}</text>
'''
        if i < len(centers) - 1:
            svg += (
                f'  <path d="M{x + 104} 245h42" stroke="{CYAN}" stroke-width="2" opacity=".65"/>\n'
            )
    svg += "</svg>\n"
    (ASSETS / "prospectiq-pipeline.svg").write_text(svg, encoding="utf-8")


def build_architecture_svg() -> None:
    modules = [
        ("CLI", "arguments + dispatch"),
        ("SOURCE REGISTRY", "authoritative source list"),
        ("SCRAPERS", "typed source adapters"),
        ("LEAD.FROM_RAW()", "normalization boundary"),
        ("ENRICHMENT", "evidence collection"),
        ("CANDIDATE SELECTION", "provenance + confidence"),
        ("SCORING", "documented additive rules"),
        ("CSV EXPORT", "stable local schema"),
    ]
    width, height = 1440, 640
    svg = _svg_header(
        width,
        height,
        "ProspectIQ architecture",
        "The CLI routes through the source registry and scrapers into normalization, enrichment, candidate selection, scoring, and CSV export.",
    )
    svg += """  <text x="72" y="62" class="eyebrow">ARCHITECTURE</text>
  <text x="72" y="102" class="title">Explicit boundaries. Inspectable flow.</text>
"""
    card_w, card_h = 278, 130
    positions = [(80 + col * 340, 150 + row * 220) for row in range(2) for col in range(4)]
    for i, ((label, subtitle), (x, y)) in enumerate(zip(modules, positions, strict=True)):
        stroke = GOLD if label in {"LEAD.FROM_RAW()", "SOURCE REGISTRY"} else GLASS_TEAL
        svg += f'''  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="16" fill="{DEEP_NAVY}" stroke="{stroke}" stroke-width="2"/>
  <text x="{x + 24}" y="{y + 54}" class="label">{label}</text>
  <text x="{x + 24}" y="{y + 88}" class="small">{subtitle}</text>
'''
        if i < 3:
            svg += f'  <path d="M{x + card_w} {y + card_h / 2}h62" stroke="{TEAL}" stroke-width="3"/>\n'
        elif i == 3:
            svg += f'  <path d="M{x + card_w / 2} {y + card_h}v56H{x - 1020 + card_w / 2}" stroke="{GOLD}" stroke-width="3" fill="none"/>\n'
        elif i < 7:
            svg += f'  <path d="M{x + card_w} {y + card_h / 2}h62" stroke="{TEAL}" stroke-width="3"/>\n'
    svg += f'''  <circle cx="1282" cy="215" r="6" fill="{GOLD}" filter="url(#glow)"/>
  <circle cx="98" cy="435" r="6" fill="{GOLD}" filter="url(#glow)"/>
</svg>
'''
    (ASSETS / "prospectiq-architecture.svg").write_text(svg, encoding="utf-8")


def build_source_map_svg() -> None:
    sources = [
        ("INSTAGRAM", "public profiles"),
        ("TIKTOK", "creator profiles"),
        ("LINKEDIN", "own session required"),
        ("GITHUB", "public API"),
        ("YOUTUBE", "channels"),
        ("TWITCH", "public channels"),
        ("PINTEREST", "public profiles"),
        ("LINK-IN-BIO", "four providers"),
    ]
    width, height = 1440, 430
    svg = _svg_header(
        width,
        height,
        "ProspectIQ supported source map",
        "Eight source categories feed a shared source registry and normalized lead schema.",
    )
    svg += """  <text x="72" y="62" class="eyebrow">SUPPORTED SOURCES</text>
  <text x="72" y="102" class="title">Eight adapters. One normalized contract.</text>
"""
    for i, (label, subtitle) in enumerate(sources):
        row, col = divmod(i, 4)
        x, y = 72 + col * 340, 146 + row * 122
        marker = GOLD if label == "LINKEDIN" else TEAL
        svg += f'''  <rect x="{x}" y="{y}" width="304" height="94" rx="14" class="card"/>
  <circle cx="{x + 30}" cy="{y + 47}" r="8" fill="{marker}"/>
  <text x="{x + 52}" y="{y + 40}" class="label">{label}</text>
  <text x="{x + 52}" y="{y + 66}" class="small">{subtitle}</text>
'''
    svg += "</svg>\n"
    (ASSETS / "prospectiq-source-map.svg").write_text(svg, encoding="utf-8")


def build_score_svg() -> None:
    width, height = 1440, 520
    svg = _svg_header(
        width,
        height,
        "ProspectIQ scoring and provenance",
        "Record completeness creates the lead score while email evidence records source, confidence, and verification separately.",
    )
    svg += f'''  <text x="72" y="62" class="eyebrow">SCORING + PROVENANCE</text>
  <text x="72" y="102" class="title">Two signals, kept deliberately separate</text>
  <rect x="72" y="148" width="620" height="300" rx="18" class="card"/>
  <text x="108" y="196" class="label">RECORD COMPLETENESS → LEAD SCORE</text>
  <text x="108" y="228" class="small">How actionable and complete is this record?</text>
  <path d="M128 295H622" stroke="{STRUCTURAL_NAVY}" stroke-width="16" stroke-linecap="round"/>
  <path d="M128 295H512" stroke="{TEAL}" stroke-width="16" stroke-linecap="round"/>
  <circle cx="512" cy="295" r="13" fill="{GOLD}" filter="url(#glow)"/>
  <text x="108" y="352" class="small">email  +  phone  +  website  +  company  +  audience signals</text>
  <text x="108" y="398" class="eyebrow">NOT PURCHASE INTENT</text>
  <rect x="748" y="148" width="620" height="300" rx="18" class="card"/>
  <text x="784" y="196" class="label">EMAIL CANDIDATE → EVIDENCE</text>
  <text x="784" y="228" class="small">What was observed, inferred, or confirmed?</text>
  <rect x="784" y="266" width="244" height="54" rx="9" fill="{STRUCTURAL_NAVY}"/>
  <text x="804" y="299" class="small">email_source</text>
  <rect x="1044" y="266" width="286" height="54" rx="9" fill="{STRUCTURAL_NAVY}"/>
  <text x="1064" y="299" class="small">email_confidence</text>
  <rect x="784" y="336" width="244" height="54" rx="9" fill="{STRUCTURAL_NAVY}"/>
  <text x="804" y="369" class="small">email_verified</text>
  <rect x="1044" y="336" width="286" height="54" rx="9" fill="{STRUCTURAL_NAVY}"/>
  <text x="1064" y="369" class="small">unconfirmed ≠ invalid</text>
</svg>
'''
    (ASSETS / "prospectiq-score-explainer.svg").write_text(svg, encoding="utf-8")


def _draw_grid(draw: ImageDraw.ImageDraw, width: int, height: int, *, spacing: int = 64) -> None:
    color = (*ImageColor(STRUCTURAL_NAVY), 70)
    for x in range(0, width, spacing):
        draw.line((x, 0, x, height), fill=color, width=1)
    for y in range(0, height, spacing):
        draw.line((0, y, width, y), fill=color, width=1)


def ImageColor(value: str) -> tuple[int, int, int]:
    """Convert a hex color to an RGB tuple."""
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _cover_backdrop(size: tuple[int, int]) -> Image.Image:
    source = ASSETS / "prospectiq-cover.png"
    if source.is_file():
        image = Image.open(source).convert("RGB")
        ratio = max(size[0] / image.width, size[1] / image.height)
        resized = image.resize(
            (round(image.width * ratio), round(image.height * ratio)), Image.Resampling.LANCZOS
        )
        left = (resized.width - size[0]) // 2
        top = (resized.height - size[1]) // 2
        image = resized.crop((left, top, left + size[0], top + size[1]))
        veil = Image.new("RGBA", size, (*ImageColor(MIDNIGHT), 86))
        return Image.alpha_composite(image.convert("RGBA"), veil).convert("RGB")

    image = Image.new("RGBA", size, (*ImageColor(MIDNIGHT), 255))
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_grid(draw, *size)
    for radius, alpha in [(280, 18), (190, 24), (110, 34)]:
        cx, cy = int(size[0] * 0.79), int(size[1] * 0.43)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=(*ImageColor(TEAL), alpha),
            width=2,
        )
    return image.convert("RGB")


def build_hero_and_social() -> None:
    hero = _cover_backdrop((1600, 900)).convert("RGBA")
    draw = ImageDraw.Draw(hero, "RGBA")
    title = _font(104, bold=True)
    subtitle = _font(30)
    eyebrow = _font(18, bold=True)
    small = _font(22)
    draw.text(
        (110, 106), "OPEN-SOURCE LEAD INTELLIGENCE", font=eyebrow, fill=ImageColor(GOLD), spacing=4
    )
    draw.text((102, 150), "ProspectIQ", font=title, fill=ImageColor(WHITE))
    draw.text(
        (110, 278),
        "Public profiles → traceable, locally controlled records",
        font=subtitle,
        fill=ImageColor(CYAN),
    )

    stages = ["COLLECT", "NORMALIZE", "ENRICH", "SCORE", "EXPORT"]
    y = 540
    xs = [190, 490, 790, 1090, 1390]
    draw.line((xs[0], y, xs[-1], y), fill=ImageColor(GLASS_TEAL), width=6)
    for i, (x, stage) in enumerate(zip(xs, stages, strict=True)):
        accent = ImageColor(GOLD if i >= 3 else TEAL)
        draw.rounded_rectangle(
            (x - 108, y - 74, x + 108, y + 74),
            radius=18,
            fill=(*ImageColor(DEEP_NAVY), 232),
            outline=(*accent, 245),
            width=3,
        )
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=accent)
        box = draw.textbbox((0, 0), stage, font=small)
        draw.text((x - (box[2] - box[0]) / 2, y + 96), stage, font=small, fill=ImageColor(WHITE))
    draw.text(
        (110, 810), "STRUCTURE  ·  PROVENANCE  ·  CONTROL", font=eyebrow, fill=ImageColor(SLATE)
    )
    hero.convert("P", palette=Image.Palette.ADAPTIVE, colors=256).convert("RGB").save(
        ASSETS / "prospectiq-readme-hero.png", optimize=True
    )

    social = _cover_backdrop((1280, 640)).convert("RGBA")
    d = ImageDraw.Draw(social, "RGBA")
    d.rounded_rectangle(
        (68, 64, 1212, 576),
        radius=28,
        fill=(*ImageColor(MIDNIGHT), 196),
        outline=(*ImageColor(GLASS_TEAL), 210),
        width=2,
    )
    d.text((120, 126), "ProspectIQ", font=_font(92, bold=True), fill=ImageColor(WHITE))
    d.text(
        (126, 252),
        "OPEN-SOURCE LEAD INTELLIGENCE",
        font=_font(19, bold=True),
        fill=ImageColor(GOLD),
    )
    d.text(
        (126, 310),
        "Public profiles → structured, traceable records",
        font=_font(29),
        fill=ImageColor(CYAN),
    )
    d.line((126, 420, 1088, 420), fill=ImageColor(GLASS_TEAL), width=4)
    for x, label in zip(
        [126, 360, 594, 828, 1062],
        ["COLLECT", "NORMALIZE", "ENRICH", "SCORE", "EXPORT"],
        strict=True,
    ):
        d.ellipse((x - 7, 413, x + 7, 427), fill=ImageColor(GOLD if x >= 828 else TEAL))
        d.text((x - 3, 455), label, anchor="ma", font=_font(16, bold=True), fill=ImageColor(SLATE))
    social.convert("RGB").save(ASSETS / "prospectiq-social-preview.png", optimize=True)


def build_pipeline_gif() -> None:
    width, height = 1440, 480
    frames: list[Image.Image] = []
    centers = [170, 445, 720, 995, 1270]
    labels = ["COLLECT", "NORMALIZE", "ENRICH", "SCORE", "EXPORT"]
    for index in range(60):
        frame = Image.new("RGB", (width, height), ImageColor(MIDNIGHT))
        draw = ImageDraw.Draw(frame, "RGBA")
        _draw_grid(draw, width, height, spacing=56)
        draw.text(
            (64, 48),
            "PUBLIC DATA → STRUCTURED RECORDS",
            font=_font(18, bold=True),
            fill=ImageColor(GOLD),
        )
        draw.text(
            (64, 88),
            "Collect. Normalize. Enrich. Score. Export.",
            font=_font(30, bold=True),
            fill=ImageColor(WHITE),
        )
        y = 250
        draw.line((centers[0], y, centers[-1], y), fill=ImageColor(GLASS_TEAL), width=5)
        progress = index / 59 * (len(centers) - 1)
        for i, (x, label) in enumerate(zip(centers, labels, strict=True)):
            reached = i <= progress
            accent = ImageColor(GOLD if abs(progress - i) < 0.42 else TEAL)
            draw.rounded_rectangle(
                (x - 96, y - 68, x + 96, y + 68),
                radius=16,
                fill=(*ImageColor(DEEP_NAVY), 240),
                outline=(*accent, 255 if reached else 105),
                width=3,
            )
            dot_radius = 10 if reached else 6
            draw.ellipse(
                (x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
                fill=(*accent, 255 if reached else 120),
            )
            text_box = draw.textbbox((0, 0), label, font=_font(19, bold=True))
            draw.text(
                (x - (text_box[2] - text_box[0]) / 2, y + 92),
                label,
                font=_font(19, bold=True),
                fill=ImageColor(WHITE if reached else SLATE),
            )
        pulse_x = centers[0] + (centers[-1] - centers[0]) * (index / 59)
        draw.ellipse((pulse_x - 12, y - 12, pulse_x + 12, y + 12), fill=ImageColor(BRIGHT_GOLD))
        for lane in range(3):
            offset = ((index * 18 + lane * 120) % (width + 160)) - 80
            draw.line(
                (offset - 70, 398 + lane * 15, offset + 70, 398 + lane * 15),
                fill=(*ImageColor(CYAN), 95),
                width=2,
            )
        frames.append(frame.quantize(colors=96, method=Image.Quantize.FASTOCTREE))
    frames[0].save(
        ASSETS / "prospectiq-pipeline.gif",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        optimize=True,
        disposal=2,
    )


def _capture_demo() -> list[str]:
    """Run the real offline demo and return privacy-safe output lines."""
    python_path = os.pathsep.join(
        part for part in (str(ROOT), os.environ.get("PYTHONPATH", "")) if part
    )
    with tempfile.TemporaryDirectory(prefix="prospectiq-readme-") as temp_dir:
        result = subprocess.run(
            [sys.executable, "-m", "prospectiq", "--demo", "--no-color"],
            cwd=temp_dir,
            env={
                **dict(os.environ),
                "NO_COLOR": "1",
                "COLUMNS": "220",
                "PYTHONPATH": python_path,
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    text = result.stdout.replace("\r\n", "\n")
    text = re.sub(r"[A-Z]:\\[^\n]*?\\demo_output\\", "demo_output/", text)
    text = re.sub(r"/[^\n]*?/demo_output/", "demo_output/", text)
    text = re.sub(
        r"prospectiq_leads_demo_\d{8}_\d{6}\.csv", "prospectiq_leads_demo_<timestamp>.csv", text
    )
    return [line.rstrip() for line in text.splitlines()]


def build_demo_gif() -> None:
    lines = _capture_demo()
    selected: list[str] = ["$ prospectiq --demo", ""]
    for line in lines:
        line = line.replace("✓", "+").replace("✗", "x")
        if len(line) > 104:
            line = line[:101] + "..."
        selected.append(line)

    width, height = 1280, 760
    line_height = 23
    top = 96
    visible_rows = 25
    frames: list[Image.Image] = []
    steps = len(selected)
    for step in range(1, steps + 1):
        frame = Image.new("RGB", (width, height), ImageColor(MIDNIGHT))
        draw = ImageDraw.Draw(frame, "RGBA")
        draw.rounded_rectangle(
            (34, 28, width - 34, height - 28),
            radius=18,
            fill=ImageColor(DEEP_NAVY),
            outline=ImageColor(GLASS_TEAL),
            width=2,
        )
        for x, color in [(66, "#D96868"), (94, GOLD), (122, TEAL)]:
            draw.ellipse((x - 7, 55 - 7, x + 7, 55 + 7), fill=ImageColor(color))
        draw.text(
            (width - 64, 47),
            "OFFLINE · FICTIONAL DATA",
            anchor="ra",
            font=_font(15, bold=True),
            fill=ImageColor(GOLD),
        )
        shown = selected[:step]
        if len(shown) > visible_rows:
            shown = shown[-visible_rows:]
        for row, line in enumerate(shown):
            color = WHITE
            if line.startswith("$"):
                color = CYAN
            elif line[:1].isdigit() and ". " in line[:4]:
                color = GOLD
            elif "✓" in line:
                color = TEAL
            elif line.startswith("  ·"):
                color = SLATE
            draw.text(
                (64, top + row * line_height),
                line,
                font=_font(16, mono=True),
                fill=ImageColor(color),
            )
        frames.append(frame.quantize(colors=128, method=Image.Quantize.FASTOCTREE))

    durations = [85] * len(frames)
    durations[-1] = 2200
    frames[0].save(
        ASSETS / "prospectiq-demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def optimize_sources() -> None:
    """Normalize supplied sources when the canonical images are present."""
    for path in (ASSETS / "prospectiq-logo-source.png", ASSETS / "prospectiq-cover.png"):
        if not path.is_file():
            continue
        with Image.open(path) as image:
            image.convert("RGB").save(path, optimize=True)


def build_logo_derivatives() -> None:
    """Create a dark lockup from the canonical logo without redrawing it."""
    source = ASSETS / "prospectiq-logo-source.png"
    if not source.is_file():
        return

    logo = Image.open(source).convert("RGBA")
    pixels = logo.load()
    for y in range(logo.height):
        for x in range(logo.width):
            red, green, blue, _ = pixels[x, y]
            distance = max(0, 255 - min(red, green, blue))
            alpha = min(255, max(0, (distance - 4) * 12))
            pixels[x, y] = (red, green, blue, alpha)

    alpha = logo.getchannel("A")
    box = alpha.getbbox()
    if box is None:
        return
    logo = logo.crop(box)
    target = Image.new("RGBA", (1000, 360), (*ImageColor(MIDNIGHT), 255))
    ratio = min(880 / logo.width, 260 / logo.height)
    logo = logo.resize(
        (max(1, round(logo.width * ratio)), max(1, round(logo.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    target.alpha_composite(
        logo,
        ((target.width - logo.width) // 2, (target.height - logo.height) // 2),
    )
    target.save(ASSETS / "prospectiq-logo-dark.png", optimize=True)


def write_tape() -> None:
    tape = """# Reproducible terminal recording; the GIF in this repository is rendered
# locally from the same real command by build_readme_assets.py.
Output docs/assets/prospectiq-demo.gif
Set Shell "powershell"
Set FontSize 17
Set Width 1280
Set Height 760
Set TypingSpeed 45ms
Set Theme { "background": "#001019", "foreground": "#F5F8FA", "black": "#001019", "brightBlack": "#8FA5B0", "cyan": "#2999A3", "brightCyan": "#9CC6CF", "yellow": "#C9B171", "brightYellow": "#D6A84B" }
Type "prospectiq --demo --no-color"
Enter
Sleep 12s
"""
    (ASSETS / "prospectiq-demo.tape").write_text(tape, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-demo", action="store_true", help="do not run and capture the CLI demo"
    )
    args = parser.parse_args()

    ASSETS.mkdir(parents=True, exist_ok=True)
    optimize_sources()
    build_logo_derivatives()
    build_pipeline_svg()
    build_architecture_svg()
    build_source_map_svg()
    build_score_svg()
    build_hero_and_social()
    build_pipeline_gif()
    write_tape()
    if not args.skip_demo:
        build_demo_gif()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
