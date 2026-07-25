## What this changes

<!-- What does this PR do, and why? Link any issue it closes: Closes #123 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] New source
- [ ] Refactor (no behaviour change)
- [ ] Documentation
- [ ] Tooling or CI

## Checklist

- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `mypy prospectiq` passes
- [ ] `pytest` passes
- [ ] New behaviour is covered by tests that would fail without the change
- [ ] No test I added makes a real network, SMTP, or DNS request
- [ ] Public functions I added have type hints and docstrings
- [ ] CHANGELOG.md updated if behaviour changed
- [ ] README updated if user-facing behaviour changed

## Responsible use

- [ ] This does not add CAPTCHA bypass, stealth or fingerprint evasion,
      credential collection, mass messaging, or access to private data
- [ ] This does not weaken existing rate-limit defaults or safety messaging
- [ ] No credentials, cookies, API keys, or third-party personal data are
      included in the diff

## For a new source

<!-- Delete this section if not applicable. -->

- [ ] Only publicly accessible data is collected
- [ ] Registered in `scrapers/registry.py` with honest `notes` about limitations
- [ ] A delay entry was added to `SOURCE_DELAYS` in `constants.py`
- [ ] Uses `fetch_html()` so status codes map to typed errors
- [ ] Tests cover a successful parse, a not-found case, and a failure mode
- [ ] Added to the Supported Sources table in the README

## Notes for the reviewer

<!-- Anything you are unsure about, trade-offs you made, or areas needing
     particular scrutiny. -->
