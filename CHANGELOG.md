# Changelog

All notable changes to ProspectIQ are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The version is declared once, in `prospectiq/__init__.py`. `pyproject.toml` reads
it dynamically and `prospectiq --version` prints it, so the three can never drift.

## [Unreleased]

Nothing yet. See [ROADMAP.md](ROADMAP.md) for what is planned.

## [0.1.0] — 2026-07-24

Initial ProspectIQ release. The project is a rebranded and substantially
rewritten derivative of the MIT licensed [Scout](https://github.com/kiryano/Scout)
project — see [ATTRIBUTION.md](ATTRIBUTION.md) for the full lineage.

### Added

**Demo mode**
- `prospectiq --demo` runs the entire pipeline against fictional records with no
  network requests and no credentials, so the project can be evaluated in
  seconds. All demo domains use the RFC 2606 reserved namespace.

**Architecture**
- A normalized `Lead` model with `from_raw()` handling alias mapping, type
  coercion, and preservation of source-specific fields in `extra`
- A declarative source registry — adding a source now means one module plus one
  table entry
- Centralized configuration loading; no module outside `config.py` reads the
  environment
- Centralized logging with a `suppressed_logging` context manager for use around
  progress rendering
- A typed exception hierarchy distinguishing rate limits, auth failures, blocks,
  not-found, configuration, and export errors
- A shared HTTP layer that maps status codes to those errors in one place
- Constants module replacing scattered string literals

**Testing and CI**
- 272 tests covering configuration, the deprecated variable fallback, text
  extraction, scoring, export, schema stability, normalization, scraper error
  mapping, demo mode, and the CLI
- Hermetic test fixtures: HTTP mocked, SMTP hard-blocked, environment stripped
- GitHub Actions CI on Python 3.10, 3.11, and 3.12 running install, Ruff lint,
  format check, mypy, tests, and a CLI smoke test
- Pre-commit hooks and a `.pre-commit-config.yaml`

**Documentation**
- Rewritten README with architecture diagram, documented output schema, scoring
  breakdown, and an explicit responsible-use section
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `ROADMAP.md`,
  `ATTRIBUTION.md`, and this changelog
- GitHub issue templates and a pull request template

**CLI**
- Subcommands: `collect`, `sources`, `exports`, `doctor`, `demo`
- `--no-color` flag alongside standard `NO_COLOR` support
- `python -m prospectiq` entry point
- Installable `prospectiq` console script via `pyproject.toml`

### Changed

- **Renamed throughout** from Scout to ProspectIQ: CLI, package, environment
  variable prefix, output filenames, and all user-facing text
- **Default request delays raised** from 1.0–2.5s to 2.0–5.0s, with per-source
  tuning (LinkedIn 4–8s, GitHub 1–2s) and an enforced 0.5s floor
- **Rate limits now stop collection** for that source instead of being retried
- **The update checker is now opt-in and advisory.** It previously ran on every
  startup and called `sys.exit(1)` when a newer release existed, blocking the
  tool entirely. It now runs only when `PROSPECTIQ_UPDATE_CHECK=true`, never
  blocks, and points at the ProspectIQ repository
- **Exports** now write to `exports/` as `prospectiq_leads_<source>_<timestamp>.csv`
  with a stable, documented column order rather than whatever keys the first
  record happened to have
- **SMTP verification** reports results as unconfirmed rather than implying
  invalidity, and detects catch-all domains explicitly
- Packaging moved to `pyproject.toml`; `requirements.txt` now installs the
  project so the two cannot drift
- Terminal presentation rebuilt around a Carolina blue palette with ASCII
  fallbacks for terminals that cannot render box-drawing characters

### Deprecated

- `SCOUT_PROXY`, `SCOUT_PROXY_FILE`, `SCOUT_FREE_PROXY`, `SCOUT_DELAY_MIN`, and
  `SCOUT_DELAY_MAX` are still read as fallbacks and emit a non-blocking warning.
  Rename them to their `PROSPECTIQ_` equivalents. They will be removed in a
  future release.

### Removed

- The upstream project's Discord badge, community links, and screenshot
- The forced-update exit path
- `app/` package and `scout.py` entry point, superseded by `prospectiq/`

### Security

- `.gitignore` now covers `.env`, cookie files, proxy lists, logs, and every
  generated CSV
- CSV export escapes values beginning with `=`, `+`, `-`, or `@` to prevent
  spreadsheet formula injection from scraped bio text
- Export filename components are sanitized against path traversal
- SMTP verification uses a non-routable HELO identity and never sends mail

[Unreleased]: https://github.com/davishiggins/prospectiq/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/davishiggins/prospectiq/releases/tag/v0.1.0
