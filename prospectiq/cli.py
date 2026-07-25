"""Command-line entry point.

Parses arguments, wires up configuration and logging, and dispatches to a
handler. With no arguments it launches the interactive menu.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from prospectiq import __version__
from prospectiq.branding import (
    build_console,
    enable_utf8_stdout,
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
)
from prospectiq.config import Config, get_deprecation_warnings, load_config
from prospectiq.constants import APP_DESCRIPTION, APP_NAME, ISSUES_URL, REPO_URL
from prospectiq.demo import run_demo
from prospectiq.exporters import export_leads, list_exports
from prospectiq.logging_config import configure_logging, get_logger, suppressed_logging
from prospectiq.models import Lead
from prospectiq.scrapers import SOURCES, collect, source_keys
from prospectiq.updates import check_for_update, update_message
from prospectiq.utilities.errors import (
    ConfigurationError,
    ExportError,
    ProspectIQError,
    RateLimitedError,
    ScraperError,
)
from prospectiq.utilities.net import polite_delay, test_connection

logger = get_logger(__name__)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="prospectiq",
        description=f"{APP_NAME} — {APP_DESCRIPTION}",
        epilog=f"Docs and issues: {REPO_URL}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run an offline demo with fictional data (no network, no credentials)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    parser.add_argument("--no-color", action="store_true", help="disable colored output")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    collect_parser = subparsers.add_parser("collect", help="collect profiles from a source")
    collect_parser.add_argument(
        "-s",
        "--source",
        required=True,
        choices=source_keys(),
        help="source to collect from",
    )
    collect_parser.add_argument(
        "-u",
        "--username",
        action="append",
        default=[],
        metavar="NAME",
        help="username to collect; repeatable",
    )
    collect_parser.add_argument(
        "-i",
        "--input",
        type=Path,
        metavar="FILE",
        help="read usernames from a .txt or .csv file, one per line",
    )
    collect_parser.add_argument("-o", "--output", type=Path, metavar="DIR", help="export directory")
    collect_parser.add_argument(
        "--no-enrich", action="store_true", help="skip the enrichment stage"
    )
    collect_parser.add_argument(
        "--no-export", action="store_true", help="print results without writing a CSV"
    )

    subparsers.add_parser("sources", help="list supported sources")
    subparsers.add_parser("exports", help="list previous CSV exports")
    subparsers.add_parser("demo", help="run the offline demo")
    subparsers.add_parser("doctor", help="check configuration and connectivity")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        A process exit code.
    """
    # Must happen before parsing: argparse writes --help and --version straight
    # to stdout and exits, which mangles non-ASCII on a legacy Windows console.
    enable_utf8_stdout()

    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(verbose=args.verbose)

    config = load_config()
    if args.no_color:
        config = Config(**{**config.__dict__, "no_color": True})

    console = build_console(config)

    for warning in get_deprecation_warnings():
        print_warning(console, warning)

    try:
        return _dispatch(args, console, config)
    except KeyboardInterrupt:
        console.print()
        print_info(console, "Interrupted.")
        return EXIT_INTERRUPTED
    except ProspectIQError as exc:
        print_error(console, str(exc))
        return EXIT_ERROR
    except Exception as exc:
        logger.exception("Unhandled error")
        print_error(console, f"Unexpected error: {exc}")
        print_info(console, f"Please report this at {ISSUES_URL}")
        return EXIT_ERROR


def _dispatch(args: argparse.Namespace, console: Console, config: Config) -> int:
    """Route parsed arguments to the matching handler."""
    if args.demo or args.command == "demo":
        run_demo(console)
        return EXIT_OK

    if args.command == "sources":
        return _cmd_sources(console, config)
    if args.command == "exports":
        return _cmd_exports(console, config)
    if args.command == "doctor":
        return _cmd_doctor(console, config)
    if args.command == "collect":
        return _cmd_collect(args, console, config)

    from prospectiq.interactive import run_interactive

    _notify_update(console, config)
    return run_interactive(console, config)


def _notify_update(console: Console, config: Config) -> None:
    """Print an advisory if a newer release exists. Never blocks."""
    latest = check_for_update(enabled=config.update_check)
    if latest:
        print_info(console, update_message(latest))


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def _cmd_sources(console: Console, config: Config) -> int:
    """List every supported source and whether it is currently usable."""
    print_section(console, "Supported sources")
    console.print()

    for source in SOURCES.values():
        available, reason = source.is_available(config)
        auth = "session cookie" if source.requires_auth else "none"
        status = "[success]ready[/success]" if available else f"[warning]{reason}[/warning]"
        console.print(
            f"  [accent]{source.key:<10}[/accent] [body]{source.label:<14}[/body] "
            f"[muted]auth: {auth:<16}[/muted] {status}"
        )
        if source.notes:
            console.print(f"             [muted]{source.notes}[/muted]")
    console.print()
    return EXIT_OK


def _cmd_exports(console: Console, config: Config) -> int:
    """List previously written export files."""
    print_section(console, "Exports", str(config.output_dir))
    console.print()

    files = list_exports(config.output_dir)
    if not files:
        print_info(console, "No exports yet. Run a collection to create one.")
        console.print()
        return EXIT_OK

    for path in files:
        size_kb = path.stat().st_size / 1024
        console.print(f"  [body]{path.name}[/body]  [muted]{size_kb:.1f} KB[/muted]")
    console.print()
    return EXIT_OK


def _cmd_doctor(console: Console, config: Config) -> int:
    """Report configuration state and check outbound connectivity."""
    print_section(console, "Configuration")
    console.print()
    print_info(console, f"Output directory : {config.output_dir}")
    print_info(console, f"Proxy mode       : {config.proxy_mode}")
    print_info(console, f"Request delay    : {config.delay_min:g}-{config.delay_max:g}s")
    print_info(console, f"SMTP verification: {'on' if config.smtp_verify else 'off'}")
    print_info(console, f"Update check     : {'on' if config.update_check else 'off'}")
    print_info(
        console,
        f"LinkedIn cookie  : {'configured' if config.has_linkedin_cookie() else 'not set'}",
    )
    print_info(
        console,
        f"Hunter.io key    : {'configured' if config.hunter_api_key else 'not set'}",
    )

    print_section(console, "Connectivity")
    console.print()
    ok, detail = test_connection(config)
    if ok:
        print_success(console, f"Outbound connection works (egress IP {detail})")
    else:
        print_error(console, f"Connection failed: {detail}")
    console.print()
    return EXIT_OK if ok else EXIT_ERROR


def _cmd_collect(args: argparse.Namespace, console: Console, config: Config) -> int:
    """Collect, enrich, and export profiles for one source."""
    identifiers = list(args.username)
    if args.input:
        identifiers.extend(read_identifiers(args.input))

    if not identifiers:
        print_error(console, "No usernames supplied. Use --username or --input.")
        return EXIT_ERROR

    output_dir = args.output or config.output_dir

    leads = collect_many(console, config, args.source, identifiers)
    if not leads:
        print_warning(console, "No profiles were collected.")
        return EXIT_ERROR

    if not args.no_enrich:
        leads = enrich_many(console, config, leads)

    from prospectiq.branding import lead_table

    console.print()
    console.print(lead_table(leads, title=f"{len(leads)} leads"))
    console.print()

    if args.no_export:
        return EXIT_OK

    try:
        path = export_leads(leads, output_dir, source=args.source)
    except ExportError as exc:
        print_error(console, str(exc))
        return EXIT_ERROR

    print_success(console, f"Exported {len(leads)} leads to [body]{path}[/body]")
    console.print()
    return EXIT_OK


# --------------------------------------------------------------------------
# Shared pipeline helpers, reused by the interactive menu
# --------------------------------------------------------------------------


def read_identifiers(path: Path) -> list[str]:
    """Read usernames from a text or CSV file.

    For CSV files, a ``username``/``handle`` column is used when present,
    otherwise the first column.

    Raises:
        ConfigurationError: The file is missing or unreadable.
    """
    if not path.is_file():
        raise ConfigurationError(f"Input file not found: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Could not read {path}: {exc}") from exc

    if path.suffix.lower() == ".csv":
        import csv
        import io

        rows = list(csv.DictReader(io.StringIO(text)))
        identifiers = []
        for row in rows:
            value = ""
            for key in ("username", "Username", "handle", "Handle"):
                if row.get(key):
                    value = row[key]
                    break
            if not value and row:
                value = next(iter(row.values()), "") or ""
            value = value.strip().lstrip("@")
            if value:
                identifiers.append(value)
        return identifiers

    return [line.strip().lstrip("@") for line in text.splitlines() if line.strip()]


def collect_many(
    console: Console,
    config: Config,
    source_key: str,
    identifiers: list[str],
    verbose: bool = False,
) -> list[Lead]:
    """Collect several profiles from one source, pacing between requests.

    Individual failures are reported and skipped. A rate limit stops the run
    immediately, because continuing would compound the problem.
    """
    source = SOURCES[source_key]
    delay = config.delay_for(source_key)
    leads: list[Lead] = []

    print_section(console, source.label, f"{len(identifiers)} to collect")
    console.print()

    for index, identifier in enumerate(identifiers, start=1):
        position = f"[muted]({index}/{len(identifiers)})[/muted]"
        try:
            with suppressed_logging(not verbose):
                lead = collect(source_key, identifier, config)
        except RateLimitedError as exc:
            print_error(console, str(exc))
            print_warning(console, "Stopping collection for this source.")
            break
        except ScraperError as exc:
            print_error(console, f"{identifier} — {exc} {position}")
            continue
        except ConfigurationError as exc:
            print_error(console, str(exc))
            break

        if lead is None:
            print_warning(console, f"{identifier} — no usable public data {position}")
            continue

        leads.append(lead)
        followers = f"{lead.follower_count:,} followers" if lead.follower_count else "collected"
        print_success(
            console,
            f"{lead.display_name or lead.username} [muted]{followers}[/muted] {position}",
        )

        if index < len(identifiers):
            polite_delay(delay)

    console.print()
    print_info(console, f"Collected {len(leads)}/{len(identifiers)} profiles.")
    return leads


def enrich_many(console: Console, config: Config, leads: list[Lead]) -> list[Lead]:
    """Run the enrichment pipeline over collected leads."""
    from prospectiq.enrichment import LeadEnricher

    print_section(console, "Enrichment", f"{len(leads)} leads")
    console.print()

    before_emails = sum(1 for lead in leads if lead.email)
    before_phones = sum(1 for lead in leads if lead.phone)

    with LeadEnricher(config) as enricher:
        for index, lead in enumerate(leads, start=1):
            try:
                enricher.enrich(lead)
            except Exception as exc:
                logger.debug("Enrichment failed for %s: %s", lead.username, exc)
            print_info(
                console,
                f"[muted]({index}/{len(leads)})[/muted] {lead.username} → "
                f"{lead.email or 'no email'}",
            )

    new_emails = sum(1 for lead in leads if lead.email) - before_emails
    new_phones = sum(1 for lead in leads if lead.phone) - before_phones
    average = sum(lead.lead_score for lead in leads) // max(len(leads), 1)

    console.print()
    print_info(
        console,
        f"Found {new_emails} new emails and {new_phones} new phone numbers. "
        f"Average lead score: {average}/100.",
    )
    return leads


if __name__ == "__main__":
    sys.exit(main())
