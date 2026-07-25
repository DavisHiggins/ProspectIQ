# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| < 0.1 | No |

ProspectIQ is pre-1.0. Security fixes land on the latest release only.

## Reporting a vulnerability

**Do not open a public issue for a security vulnerability.**

Report it privately through
[GitHub Security Advisories](https://github.com/davishiggins/prospectiq/security/advisories/new),
or by email to the address on https://davishiggins.com.

Please include:

- What the issue is and what an attacker could achieve
- Steps to reproduce, ideally with a minimal case
- Affected version and platform
- Any suggested fix

**What to expect:** acknowledgement within 72 hours, an assessment within a week,
and a fix released as promptly as severity warrants. You will be credited in the
advisory and changelog unless you prefer otherwise. This is a solo-maintained
project, so please allow reasonable time before public disclosure.

## In scope

- Code execution, path traversal, or injection through crafted profile data
- Leakage of credentials, cookies, or API keys into logs, exports, or error output
- CSV injection or other export-format attacks
- Dependency vulnerabilities that ProspectIQ actually exposes
- Failures in the safety controls described below

## Out of scope

- Vulnerabilities in the third-party platforms ProspectIQ reads from — report
  those to the platform
- A source blocking or rate limiting you; that is the source working correctly
- Requests to add challenge-bypass or evasion capability. These are deliberate
  omissions, not oversights
- Misuse of the tool by its operator. Legal responsibility for how you use it is
  yours

## Handling credentials

ProspectIQ reads three sensitive values, all optional:

| Value | Where it goes | Notes |
|---|---|---|
| `PROSPECTIQ_LINKEDIN_COOKIE` | In-memory session only | Your own exported `li_at`. Never a password. |
| `PROSPECTIQ_HUNTER_API_KEY` | Sent only to `api.hunter.io` | |
| Proxy credentials | Sent only to your proxy | Often embedded in the URL |

None are written to disk by ProspectIQ, logged at any level, or transmitted
anywhere other than the service they authenticate to.

`.gitignore` covers `.env`, `cookies.*`, `*.cookie`, `proxies.txt`, `*.pem`,
`*.key`, logs, and every generated CSV. Verify before your first commit:

```bash
git status --porcelain
git check-ignore -v .env
```

If you ever commit a credential, rotate it immediately — for LinkedIn, log out to
invalidate the session. Removing the file in a later commit does not remove it
from history.

## Built-in safety controls

- **Formula injection** — exported cells beginning with `=`, `+`, `-`, or `@` are
  prefixed with an apostrophe, since scraped bios are attacker-controlled and
  spreadsheets execute such cells
- **Path traversal** — export filename components are sanitized and resolved
- **SMTP** — verification uses a non-routable HELO identity, issues `RCPT TO`
  only, and never sends mail
- **Rate limiting** — a 429 stops collection for that source rather than
  retrying; delays have an enforced floor that configuration cannot go below
- **No unrequested network calls** — the update check is opt-in; demo mode makes
  no requests at all
- **Error output** — messages do not echo credential values

## Data protection

Exported CSVs contain personal information about real people. Running ProspectIQ
makes you the data controller for that file under GDPR, UK GDPR, and comparable
regimes.

That means you are responsible for a lawful basis for processing, honouring
access and deletion requests, storing exports securely, and — under Article 14
GDPR — notifying people whose data you collected from a source other than
themselves. Treat `exports/` as sensitive, and delete what you no longer need.

See the Responsible Use section of the [README](README.md#responsible-use).
