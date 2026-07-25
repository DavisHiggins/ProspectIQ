# Attribution

ProspectIQ is a rebranded and substantially modified derivative of an existing
open-source project. This document records that lineage plainly, because
misrepresenting authorship in an open-source project is both a licence violation
and a professional one.

## Upstream project

**Scout** — https://github.com/kiryano/Scout
Licensed under the MIT License. Copyright (c) 2026 Scout contributors.

ProspectIQ was forked from Scout at commit `171503b`. The upstream copyright
notice is retained in [LICENSE](LICENSE) as the MIT License requires, and the
git history of this repository preserves the original commits.

## What was inherited

The following ideas and implementation approaches originate with Scout:

- The overall concept: a CLI that collects public profile data from several
  social sources, enriches it with contact details, and exports to CSV
- The set of supported sources, and the endpoints and page structures each one
  is read from
- The parsing strategies for each source, including which JSON blobs and regex
  patterns yield usable profile fields
- The core enrichment idea: deep-scrape a lead's website, resolve a company
  domain, infer an email pattern, and verify candidates over SMTP
- The additive lead-scoring concept and several of its original weightings

Credit for the original research into how each source exposes public data —
which is the hard, tedious part — belongs to the Scout contributors.

## What was changed in ProspectIQ

The 0.1.0 release is a substantial rewrite rather than a rename. Specifics:

**Architecture**
- The 1,139-line `scout.py` monolith was decomposed into a package with
  separated CLI, configuration, logging, models, scrapers, enrichment,
  exporters, and utilities layers
- A normalized `Lead` model was introduced. Previously each scraper returned an
  ad-hoc dict and the CSV schema was whatever the first record's keys happened
  to be
- A declarative source registry replaced hand-maintained if/elif chains in three
  separate places
- Configuration was centralized; every module previously read `os.environ`
  directly
- A typed exception hierarchy replaced bare `Exception` handling and string
  matching on error text
- Scrapers no longer read global state; configuration is passed explicitly

**Behaviour**
- The update checker no longer forces `sys.exit(1)` on a newer release. It is
  now opt-in, advisory, and points at the ProspectIQ repository
- Default request delays were raised from 1.0–2.5s to 2.0–5.0s, with per-source
  tuning and an enforced floor
- Rate limits now stop collection for that source rather than being retried
- Exports moved to a dedicated directory with a stable, documented column order
- CSV export gained spreadsheet formula-injection protection
- SMTP verification gained explicit catch-all handling, and results are reported
  as "unconfirmed" rather than implying invalidity
- `NO_COLOR` and non-TTY output are now respected
- Added an offline demo mode

**Engineering**
- Added a test suite of 272 tests; the upstream project had none
- Added CI across Python 3.10–3.12, Ruff, mypy, and pre-commit
- Added type hints and docstrings throughout
- Added contributor, security, conduct, changelog, and roadmap documentation

**Branding**
- Renamed throughout, with `SCOUT_` environment variables retained as
  deprecated fallbacks so existing users can migrate
- New terminal presentation using a Carolina blue palette
- Removed the upstream project's Discord links, community references, and
  screenshot, none of which belong to this project

## Third-party dependencies

| Package | Licence | Used for |
|---|---|---|
| [requests](https://github.com/psf/requests) | Apache-2.0 | HTTP for most scrapers |
| [httpx](https://github.com/encode/httpx) | BSD-3-Clause | HTTP for LinkedIn and enrichment |
| [dnspython](https://github.com/rthalley/dnspython) | ISC | MX record lookups |
| [rich](https://github.com/Textualize/rich) | MIT | Terminal rendering |
| [free-proxy](https://github.com/jundymek/free-proxy) | MIT | Optional free proxy sourcing |

Development tooling: [pytest](https://github.com/pytest-dev/pytest) (MIT),
[Ruff](https://github.com/astral-sh/ruff) (MIT),
[mypy](https://github.com/python/mypy) (MIT),
[pre-commit](https://github.com/pre-commit/pre-commit) (MIT),
[Hatchling](https://github.com/pypa/hatch) (MIT).

## Maintainer

ProspectIQ is maintained by **Davis Higgins** — https://davishiggins.com

Contributions to ProspectIQ specifically are credited in
[CHANGELOG.md](CHANGELOG.md) and in the git history. Nothing in this repository
should be read as claiming original authorship of the upstream work described
above.
