# Demo screenshot — not yet captured

**Status: placeholder.** No ProspectIQ screenshot exists yet.

The upstream Scout project's screenshot was removed rather than relabelled. It
showed Scout's crimson branding and Scout's output, so presenting it as
ProspectIQ would have been misleading — the README currently ships with no
screenshot at all instead.

This file documents how to produce a legitimate one.

---

## What to capture

Use **demo mode**. It is the right subject for a README screenshot for three
reasons: it exercises the real pipeline, it needs no credentials so anyone can
reproduce it, and — most importantly — it contains no real person's contact
information.

```bash
prospectiq --demo
```

**Never screenshot a real collection run.** Doing so publishes real people's
names, emails, and phone numbers to a public repository, permanently and
indexably. That is a data-protection incident, not a marketing asset.

## Capturing it

Set the terminal to **100×40** or wider — narrower and the lead table wraps.

Recommended settings for a clean capture:

- A dark theme, so the Carolina blue accent (`#7BAFD4`) reads clearly
- A font with good box-drawing coverage: JetBrains Mono, Fira Code, or Cascadia Code
- 14pt or larger, so the image stays legible when GitHub scales it down
- Hide the shell prompt line, or run in a fresh window so no prior history shows

### Static image

| Platform | Tool |
|---|---|
| macOS | `Cmd+Shift+4`, then Space to capture the window |
| Windows | Snipping Tool (`Win+Shift+S`) |
| Linux | Flameshot, Spectacle, or GNOME Screenshot |
| Any | [carbon.now.sh](https://carbon.now.sh) or [ray.so] for a styled render |

Save as `docs/assets/prospectiq-demo.png`. Keep it under 500 KB — the
`check-added-large-files` pre-commit hook rejects anything over that.

### Animated capture

A GIF or SVG showing the pipeline running is more compelling than a still,
because the staged output is the point.

- [asciinema](https://asciinema.org) + [agg](https://github.com/asciinema/agg) —
  records a terminal session and converts it to GIF
- [vhs](https://github.com/charmbracelet/vhs) — scripts the whole recording, so
  it is reproducible and re-renderable when the UI changes
- [termtosvg](https://github.com/nbedos/termtosvg) — produces an animated SVG,
  which stays crisp at any zoom and is usually far smaller than a GIF

A `vhs` tape for this project would look roughly like:

```
Output docs/assets/prospectiq-demo.gif
Set FontSize 16
Set Width 1200
Set Height 800
Set Theme "Catppuccin Mocha"
Type "prospectiq --demo"
Enter
Sleep 12s
```

## Adding it to the README

Insert below the badge block:

```markdown
<p align="center">
  <img src="docs/assets/prospectiq-demo.gif" alt="ProspectIQ demo mode running the full pipeline: collection, normalization, enrichment, scoring, and CSV export" width="800">
</p>
```

Write a real alt text describing what the image shows — the example above is a
usable starting point. Screen-reader users and anyone on a slow connection get
nothing from `alt="screenshot"`.

Then delete this file.

## Checklist before committing

- [ ] Captured from `prospectiq --demo`, not a real collection run
- [ ] No real names, emails, phone numbers, or usernames visible
- [ ] No `.env` contents, cookies, API keys, or proxy URLs visible
- [ ] No personal file paths visible in the prompt (e.g. `/Users/yourname/`)
- [ ] Under 500 KB
- [ ] Descriptive alt text written
- [ ] This placeholder file deleted
