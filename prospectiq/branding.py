"""Terminal presentation: banner, palette, and status rendering.

Color is applied through Rich, which is disabled automatically when ``NO_COLOR``
is set or when stdout is not a TTY, so piped output stays clean.
"""

from __future__ import annotations

import contextlib
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from prospectiq import __version__
from prospectiq.config import Config
from prospectiq.constants import (
    APP_NAME,
    APP_TAGLINE,
    GLASS_TEAL,
    INTELLIGENCE_TEAL,
    REPO_SLUG,
    SIGNAL_GOLD,
    SOFT_CYAN,
    STRUCTURAL_NAVY,
)

#: Rich theme mapping semantic roles onto the ProspectIQ brand palette.
THEME = Theme(
    {
        "accent": INTELLIGENCE_TEAL,
        "accent.dim": SOFT_CYAN,
        "accent.dark": GLASS_TEAL,
        "signal": SIGNAL_GOLD,
        "structure": STRUCTURAL_NAVY,
        "success": "green",
        "warning": "yellow",
        "danger": "red",
        "body": "white",
        "muted": "dim",
        "prompt.choices": INTELLIGENCE_TEAL,
        "prompt.default": "dim",
    }
)

_WORDMARK = "██████╗ ██████╗  ██████╗ ███████╗██████╗ ███████╗ ██████╗████████╗██╗ ██████╗"

#: Rendered when the terminal is too narrow for the full wordmark.
_NARROW_WORDMARK = "▓▓▓ ProspectIQ ▓▓▓"

WORDMARK_MIN_WIDTH = 80


def enable_utf8_stdout() -> None:
    """Reconfigure stdout/stderr to UTF-8 where the platform allows it.

    Windows consoles still default to a legacy codepage that cannot encode the
    banner or box-drawing characters. Reconfiguring avoids a
    ``UnicodeEncodeError`` mid-render; :func:`supports_unicode` handles the
    cases where it is not possible.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        # A stream that refuses reconfiguration is handled by supports_unicode.
        with contextlib.suppress(OSError, ValueError):
            reconfigure(encoding="utf-8", errors="replace")


def supports_unicode() -> bool:
    """Whether stdout can encode the box-drawing characters used in the UI."""
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "─✓✗·█".encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


class Glyphs:
    """Symbols used in output, with ASCII fallbacks for limited terminals."""

    def __init__(self, unicode_ok: bool) -> None:
        self.unicode_ok = unicode_ok
        self.rule = "─" if unicode_ok else "-"
        self.check = "✓" if unicode_ok else "+"
        self.cross = "✗" if unicode_ok else "x"
        self.bullet = "·" if unicode_ok else "-"
        self.warn = "!"
        self.separator = "  ·  " if unicode_ok else "  |  "


#: Module-level glyph set, refreshed by :func:`build_console`.
GLYPHS = Glyphs(supports_unicode())


def build_console(config: Config | None = None, *, quiet: bool = False) -> Console:
    """Create the application console.

    Always use this rather than constructing a :class:`~rich.console.Console`
    directly: it installs :data:`THEME`, without which the semantic style names
    used throughout the UI (``accent``, ``success``, …) do not resolve.

    Args:
        config: Runtime configuration; supplies the ``NO_COLOR`` preference.
        quiet: Suppress all output. Useful for tests and non-interactive callers.
    """
    global GLYPHS

    enable_utf8_stdout()
    GLYPHS = Glyphs(supports_unicode())

    no_color = bool(config and config.no_color)
    return Console(
        theme=THEME,
        no_color=no_color,
        quiet=quiet,
        force_terminal=False,
        highlight=False,
        soft_wrap=False,
        legacy_windows=False if GLYPHS.unicode_ok else None,
    )


def color_enabled(console: Console) -> bool:
    """Whether the console will actually emit color."""
    return not console.no_color and console.is_terminal


def render_banner(console: Console, config: Config) -> None:
    """Print the startup banner."""
    console.print()

    if GLYPHS.unicode_ok:
        wordmark = _WORDMARK if console.width >= WORDMARK_MIN_WIDTH else _NARROW_WORDMARK
        console.print(Text(wordmark, style=f"bold {INTELLIGENCE_TEAL}"))

    console.print(
        Text.assemble(
            (APP_NAME.upper(), f"bold {INTELLIGENCE_TEAL}"),
            ("  ", ""),
            (APP_TAGLINE, "body"),
            ("  ", ""),
            (f"v{__version__}", "muted"),
        )
    )
    console.print(Text(status_line(config), style="dim"))
    console.print()


def status_line(config: Config) -> str:
    """Render a one-line summary of the active configuration."""
    proxy = {
        "custom": "proxy: custom",
        "file": "proxy: rotating",
        "free": "proxy: free (unreliable)",
        "none": "proxy: off",
    }[config.proxy_mode]

    low, high = config.delay_min, config.delay_max
    linkedin = "linkedin: ready" if config.has_linkedin_cookie() else "linkedin: not configured"

    sep = GLYPHS.separator
    return f"{REPO_SLUG}{sep}{proxy}{sep}delay: {low:g}-{high:g}s{sep}{linkedin}"


def print_success(console: Console, message: str) -> None:
    """Print a success message."""
    console.print(f"  [success]{GLYPHS.check}[/success] {message}")


def print_warning(console: Console, message: str) -> None:
    """Print a warning."""
    console.print(f"  [warning]{GLYPHS.warn}[/warning] {message}")


def print_error(console: Console, message: str) -> None:
    """Print an error."""
    console.print(f"  [danger]{GLYPHS.cross}[/danger] {message}")


def print_info(console: Console, message: str) -> None:
    """Print a neutral informational line."""
    console.print(f"  [muted]{GLYPHS.bullet}[/muted] {message}")


def print_section(console: Console, title: str, subtitle: str = "") -> None:
    """Print a section heading."""
    console.print()
    heading = Text.assemble((title, f"bold {INTELLIGENCE_TEAL}"))
    if subtitle:
        heading.append(f"  {subtitle}", style="dim")
    console.print(heading)
    console.print(Text(GLYPHS.rule * min(console.width, 72), style="accent.dark"))


def lead_table(leads: list, title: str = "Leads") -> Table:
    """Build a summary table of collected leads.

    Args:
        leads: A list of :class:`~prospectiq.models.Lead` objects.
        title: Table heading.
    """
    table = Table(
        title=title,
        title_style=f"bold {INTELLIGENCE_TEAL}",
        title_justify="left",
        header_style=f"bold {SOFT_CYAN}",
        border_style="accent.dark",
        padding=(0, 1),
    )
    table.add_column("Name", style="white", max_width=24)
    table.add_column("Source", style="dim", max_width=10)
    table.add_column("Email", style="white", max_width=32)
    table.add_column("Conf.", justify="right", max_width=6)
    table.add_column("Phone", style="dim", max_width=16)
    table.add_column("Score", justify="right", max_width=6)

    blank = "—" if GLYPHS.unicode_ok else "-"
    for lead in leads:
        confidence = f"{lead.email_confidence}%" if lead.email else blank
        table.add_row(
            lead.display_name or lead.username,
            lead.source,
            lead.email or blank,
            f"[{_score_style(lead.email_confidence)}]{confidence}[/]",
            lead.phone or blank,
            f"[{_score_style(lead.lead_score)}]{lead.lead_score}[/]",
        )

    return table


def _score_style(score: int) -> str:
    """Map a 0-100 score onto a semantic color."""
    if score >= 70:
        return "success"
    if score >= 40:
        return "warning"
    return "danger"


def responsible_use_notice(console: Console) -> None:
    """Print the responsible-use reminder shown at startup."""
    console.print(
        Panel(
            "ProspectIQ collects [bold]publicly available[/bold] information only.\n"
            "You are responsible for complying with applicable law, platform terms, "
            "and data-protection obligations, and for honouring opt-out and deletion "
            "requests for any data you export.",
            title="[accent]Responsible use[/accent]",
            border_style="accent.dark",
            padding=(0, 2),
        )
    )
