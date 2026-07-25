# Roadmap

What is planned for ProspectIQ, roughly in priority order. This is a
solo-maintained project, so treat it as direction rather than commitment — no
dates are promised.

Have an opinion? Open an issue.

## 0.2 — Output and resumability

- **JSON and JSONL exporters.** The exporter layer already abstracts format; CSV
  is simply the only implementation so far. JSONL in particular suits piping
  into other tools.
- **Resumable collection.** A run over a few hundred usernames that dies at 80%
  currently loses everything. A small state file keyed by source and identifier
  would let `--resume` pick up where it stopped.
- **Deduplication across exports.** Detect when the same person appears under
  several sources, matched on email or resolved company domain plus name, and
  optionally merge into one record.
- **`--dry-run`** to show what would be collected and the estimated wall time
  under current pacing, without making requests.

## 0.3 — Enrichment quality

- **Structured rate-limit backoff.** Sources that return `Retry-After` or
  `X-RateLimit-Reset` should be honoured precisely rather than falling back to
  the generic "stop and warn" behaviour.
- **Confidence calibration.** The current email scores are hand-tuned constants.
  Running them against a labelled set of known-correct addresses would tell us
  whether the weightings actually reflect real accuracy — and it is entirely
  possible they do not.
- **Better company-name parsing.** The current headline parser handles
  "Role at Company" well and little else. Multi-word names with punctuation, and
  headlines listing several employers, are handled poorly.
- **MX-based provider detection.** Knowing a domain sits behind Google Workspace
  or Microsoft 365 changes what SMTP verification results actually mean, and
  should feed into the confidence score.

## 0.4 — Sources and interfaces

- **Additional sources** where a clear public endpoint exists — Mastodon and
  Bluesky are the obvious candidates, both with real public APIs rather than
  HTML scraping.
- **Library-first API.** `from prospectiq import collect, enrich` as a documented,
  stable surface, so ProspectIQ can be used as a component rather than only a CLI.
- **Optional SQLite output**, for people accumulating leads over time who want
  querying rather than a pile of CSVs.

## Under consideration

Not committed, and each has a real objection:

- **Concurrent collection.** Faster, but multiplies request rate against sources
  — squarely against this project's posture. If it happens it will be opt-in,
  capped, and per-source.
- **A web UI.** Broadens the audience, but a browser interface makes it much
  easier to use carelessly and much harder to keep the responsible-use framing
  in front of the user.
- **Scheduled or watch mode.** Continuous monitoring of individuals is a
  meaningfully different and more invasive product than one-off research, and
  probably should not exist here.

## Explicitly not planned

These are permanent exclusions, not backlog items. See
[CONTRIBUTING.md](CONTRIBUTING.md#scope).

- CAPTCHA solving or challenge bypass
- Browser fingerprint spoofing or stealth automation
- Credential collection or session hijacking
- Automated outreach, mail sending, or mass messaging
- Access to private, paywalled, or access-controlled data
- Bundled or resold contact databases
