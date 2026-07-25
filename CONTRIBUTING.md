# Contributing to ProspectIQ

Thanks for considering a contribution. This document covers setup, standards, and
what will and will not be accepted.

## Scope

ProspectIQ is a responsible data-collection tool. Some contributions will be
declined on principle regardless of how well they are written:

- CAPTCHA solving, or any challenge-bypass mechanism
- Browser fingerprint spoofing or stealth automation
- Credential collection, phishing helpers, or session hijacking
- Automated mass messaging or outreach sending
- Anything that accesses private, paywalled, or access-controlled data
- Removing or weakening rate-limit defaults and safety messaging

If you are unsure whether an idea fits, open an issue before writing code. That
is cheaper for both of us than a rejected pull request.

## Setup

```bash
git clone https://github.com/davishiggins/prospectiq.git
cd prospectiq
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

Verify your environment:

```bash
pytest
prospectiq --demo
```

## Before opening a pull request

```bash
ruff check .              # lint
ruff format .             # format
mypy prospectiq           # types
pytest                    # tests
```

Pre-commit runs the first three automatically on staged files if you installed
the hooks. CI runs all four on Python 3.10, 3.11, and 3.12.

## Standards

**Style**
- Ruff handles formatting and linting; do not fight it
- Line length 100
- Type hints on every public function signature
- Google-style docstrings on public classes and functions, explaining *why* where
  the *what* is not obvious from the name
- Absolute imports (`from prospectiq.x import y`)
- Keep modules under 500 lines; split when they grow past that

**Design**
- Configuration is read in `config.py` and nowhere else. If you need a setting,
  add it there and pass a `Config` through
- Scrapers raise typed errors from `utilities/errors.py`. Never let a `requests`
  or `httpx` exception escape a scraper
- Scrapers return raw dicts. `Lead.from_raw()` owns normalization
- New constants go in `constants.py`, not inline

**Tests**
- Every behavioural change needs a test
- Tests must not touch the network, SMTP, or real credentials. The fixtures in
  `conftest.py` will fail the test if you try
- Write tests that can actually fail. A test asserting `True` is worse than no
  test, because it manufactures false confidence
- Name tests for the behaviour, not the function: `test_catch_all_domain_reduces_confidence`,
  not `test_score_email_2`

## Adding a source

1. Create `prospectiq/scrapers/<source>.py` exposing:
   ```python
   def fetch(identifier: str, config: Config) -> dict[str, Any] | None: ...
   ```
2. Use `fetch_html()` from `base.py` so status codes map to typed errors
   consistently
3. Return a raw dict using the established key names (`platform`, `username`,
   `full_name`, `bio`, …). `Lead.from_raw()` maps them
4. Add one `Source(...)` entry to `registry.py`, including honest `notes` about
   its limitations
5. Add a delay entry to `SOURCE_DELAYS` in `constants.py`
6. Add tests with mocked HTTP covering: a successful parse, a not-found case, and
   at least one failure mode
7. Add a row to the Supported Sources table in the README

Only collect publicly accessible data, and be conservative with request pacing.

## Commit messages

Conventional Commits:

```
feat: add Mastodon source
fix: handle missing MX records in domain resolution
docs: clarify SMTP verification limitations
test: cover catch-all detection
refactor: extract company name parsing
chore: bump ruff to 0.7
```

## Pull requests

- One logical change per PR
- Fill in the PR template
- Update the README and CHANGELOG when behaviour changes
- Make sure CI is green

## Reporting bugs

Use the bug report template. A useful report includes the ProspectIQ version,
Python version, OS, the exact command, and the output with `--verbose`.

**Never paste real cookies, API keys, proxy URLs with credentials, or the
personal data of third parties into an issue.** Redact before posting.

## Security issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).

## Licence

Contributions are accepted under the [MIT License](LICENSE), the same terms as
the project.
