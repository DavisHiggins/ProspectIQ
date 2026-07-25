"""The interactive menu.

A thin wrapper over the same helpers the ``collect`` subcommand uses, so both
paths run identical collection, enrichment, and export logic.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from prospectiq.branding import (
    lead_table,
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
    render_banner,
    responsible_use_notice,
)
from prospectiq.config import Config
from prospectiq.constants import DEMO_OUTPUT_DIR
from prospectiq.demo import run_demo
from prospectiq.exporters import export_leads, list_exports
from prospectiq.logging_config import get_logger
from prospectiq.models import Lead
from prospectiq.scrapers import SOURCES
from prospectiq.utilities.errors import ExportError, ProspectIQError

logger = get_logger(__name__)

EXIT_OK = 0

MENU_EXIT = "0"
MENU_BULK = "b"
MENU_DEMO = "d"
MENU_EXPORTS = "e"
MENU_CONFIG = "c"


def run_interactive(console: Console, config: Config) -> int:
    """Run the interactive menu loop until the user exits."""
    render_banner(console, config)
    responsible_use_notice(console)

    source_keys = list(SOURCES)

    while True:
        _render_menu(console, source_keys)

        choices = [str(i) for i in range(1, len(source_keys) + 1)] + [
            MENU_BULK,
            MENU_DEMO,
            MENU_EXPORTS,
            MENU_CONFIG,
            MENU_EXIT,
        ]

        try:
            choice = Prompt.ask(
                "[accent]>[/accent]", choices=choices, default=MENU_EXIT, show_choices=False
            )
        except (KeyboardInterrupt, EOFError):
            console.print()
            return EXIT_OK

        if choice == MENU_EXIT:
            console.print()
            print_info(console, "Goodbye.")
            console.print()
            return EXIT_OK

        try:
            if choice == MENU_DEMO:
                run_demo(console, Path(DEMO_OUTPUT_DIR))
            elif choice == MENU_EXPORTS:
                _show_exports(console, config)
            elif choice == MENU_CONFIG:
                _show_config(console, config)
            elif choice == MENU_BULK:
                _run_bulk(console, config, source_keys)
            else:
                _run_source(console, config, source_keys[int(choice) - 1])
        except ProspectIQError as exc:
            print_error(console, str(exc))
        except (KeyboardInterrupt, EOFError):
            console.print()
            print_info(console, "Cancelled.")

        _pause(console)


def _render_menu(console: Console, source_keys: list[str]) -> None:
    """Print the main menu."""
    print_section(console, "Sources")
    console.print()

    for index, key in enumerate(source_keys, start=1):
        source = SOURCES[key]
        auth = " [muted](needs cookie)[/muted]" if source.requires_auth else ""
        console.print(f"  [accent]{index}[/accent]  [body]{source.label}[/body]{auth}")

    console.print()
    print_section(console, "Tools")
    console.print()
    console.print(
        f"  [accent]{MENU_BULK}[/accent]  [body]Bulk collect[/body] [muted]from a file[/muted]"
    )
    console.print(
        f"  [accent]{MENU_DEMO}[/accent]  [body]Demo[/body] [muted]offline sample run[/muted]"
    )
    console.print(
        f"  [accent]{MENU_EXPORTS}[/accent]  [body]Exports[/body] [muted]list CSV files[/muted]"
    )
    console.print(f"  [accent]{MENU_CONFIG}[/accent]  [body]Configuration[/body]")
    console.print(f"  [accent]{MENU_EXIT}[/accent]  [body]Exit[/body]")
    console.print()


def _run_source(console: Console, config: Config, source_key: str) -> None:
    """Prompt for usernames and run the pipeline for one source."""
    from prospectiq.cli import collect_many

    source = SOURCES[source_key]

    available, reason = source.is_available(config)
    if not available:
        print_error(console, f"{source.label} is unavailable: {reason}")
        if source_key == "linkedin":
            _linkedin_help(console)
        return

    identifiers = _prompt_identifiers(console, source.label, source.input_label)
    if not identifiers:
        return

    leads = collect_many(console, config, source_key, identifiers)
    if not leads:
        print_warning(console, "Nothing was collected.")
        return

    _finish(console, config, leads, source_key)


def _run_bulk(console: Console, config: Config, source_keys: list[str]) -> None:
    """Collect from a file of usernames."""
    from prospectiq.cli import collect_many, read_identifiers

    raw_path = Prompt.ask("[accent]File path[/accent]", default="usernames.txt")
    identifiers = read_identifiers(Path(raw_path.strip()))
    if not identifiers:
        print_warning(console, "That file contained no usernames.")
        return

    print_info(console, f"Found {len(identifiers)} usernames.")
    console.print()
    for index, key in enumerate(source_keys, start=1):
        console.print(f"  [accent]{index}[/accent]  [body]{SOURCES[key].label}[/body]")
    console.print()

    choice = Prompt.ask(
        "[accent]Source[/accent]",
        choices=[str(i) for i in range(1, len(source_keys) + 1)],
        default="1",
    )
    source_key = source_keys[int(choice) - 1]

    if not Confirm.ask(
        f"Collect {len(identifiers)} profiles from {SOURCES[source_key].label}?",
        default=True,
    ):
        return

    leads = collect_many(console, config, source_key, identifiers)
    if leads:
        _finish(console, config, leads, source_key)


def _finish(console: Console, config: Config, leads: list[Lead], source_key: str) -> None:
    """Offer enrichment and export for a collected batch."""
    from prospectiq.cli import enrich_many

    if Confirm.ask("\nEnrich leads with contact info?", default=True):
        enrich_many(console, config, leads)

    console.print()
    console.print(lead_table(leads, title=f"{len(leads)} leads"))
    console.print()

    if not Confirm.ask("Export to CSV?", default=True):
        return

    try:
        path = export_leads(leads, config.output_dir, source=source_key)
    except ExportError as exc:
        print_error(console, str(exc))
        return

    print_success(console, f"Exported to [body]{path}[/body]")


def _prompt_identifiers(console: Console, label: str, input_label: str) -> list[str]:
    """Collect usernames one per line until an empty line is entered."""
    console.print()
    print_info(console, f"Enter {label} {input_label.lower()}s, one per line.")
    print_info(console, "Press Enter on an empty line when finished.")
    console.print()

    identifiers: list[str] = []
    while True:
        entry = Prompt.ask(f"[accent]{input_label}[/accent]", default="").strip()
        if not entry:
            break
        cleaned = entry.lstrip("@").strip()
        if cleaned:
            identifiers.append(cleaned)
            print_success(console, cleaned)

    if not identifiers:
        print_warning(console, "No usernames entered.")
    return identifiers


def _show_exports(console: Console, config: Config) -> None:
    """List previous exports."""
    print_section(console, "Exports", str(config.output_dir))
    console.print()

    files = list_exports(config.output_dir)
    if not files:
        print_info(console, "No exports yet.")
        return

    for path in files:
        size_kb = path.stat().st_size / 1024
        console.print(f"  [body]{path.name}[/body]  [muted]{size_kb:.1f} KB[/muted]")


def _show_config(console: Console, config: Config) -> None:
    """Show the active configuration and where to change it."""
    print_section(console, "Configuration", "set via .env or environment variables")
    console.print()
    print_info(console, f"Output directory : {config.output_dir}")
    print_info(console, f"Proxy mode       : {config.proxy_mode}")
    print_info(console, f"Request delay    : {config.delay_min:g}-{config.delay_max:g}s")
    print_info(console, f"SMTP verification: {'on' if config.smtp_verify else 'off'}")
    print_info(
        console,
        f"LinkedIn cookie  : {'configured' if config.has_linkedin_cookie() else 'not set'}",
    )
    print_info(
        console,
        f"Hunter.io key    : {'configured' if config.hunter_api_key else 'not set'}",
    )
    console.print()
    print_info(console, "Copy .env.example to .env to change these settings.")


def _linkedin_help(console: Console) -> None:
    """Explain how to supply a LinkedIn session cookie."""
    console.print()
    print_info(console, "LinkedIn uses your own session cookie:")
    console.print("    1. Log into LinkedIn in your browser")
    console.print("    2. DevTools (F12) → Application → Cookies → linkedin.com")
    console.print("    3. Copy the value of [body]li_at[/body]")
    console.print("    4. Add [body]PROSPECTIQ_LINKEDIN_COOKIE=<value>[/body] to .env")
    console.print()
    print_warning(
        console,
        "Treat that cookie like a password. Never commit it, and never share it.",
    )


def _pause(console: Console) -> None:
    """Wait for the user before redrawing the menu."""
    console.print()
    try:
        Prompt.ask("[muted]Press Enter to continue[/muted]", default="")
    except (KeyboardInterrupt, EOFError):
        console.print()
