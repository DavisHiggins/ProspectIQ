# ProspectIQ README — World-Class Brand & Experience Overhaul

## Repository

```text
https://github.com/DavisHiggins/ProspectIQ
```

## Task Type

README / repository presentation / brand system / developer experience overhaul.

This task is intentionally focused on **README presentation and supporting README assets**. Do not perform unrelated scraper, enrichment, scoring, export, networking, or product-logic changes.

---

# 0. Mission

Rebuild the ProspectIQ README into an exceptionally polished, professional, easy-to-use open-source product page that feels closer to a premium product launch page than a default GitHub README.

The finished README must:

- immediately communicate what ProspectIQ is;
- visually match the supplied ProspectIQ cover artwork;
- use the supplied ProspectIQ logo;
- feel sophisticated, modern, technical, and trustworthy;
- make installation and first use obvious;
- explain the pipeline visually;
- make deeper documentation easy to navigate;
- preserve the repository's technical credibility;
- remain fast and usable on desktop and mobile;
- use motion intelligently without becoming distracting;
- look coherent in both GitHub light and dark themes;
- remain fully functional when images do not load;
- preserve responsible-use and attribution requirements;
- never invent capabilities, usage metrics, customer results, or accuracy claims.

The quality bar is not “a nicer README.”

The quality bar is:

> A README that a senior engineer, recruiter, open-source contributor, or product designer can open and immediately understand that ProspectIQ is a serious, intentional, well-engineered project.

Treat the README as ProspectIQ's public product surface.

---

# 1. Read the Repository Before Editing

Before making any change, inspect the entire repository and specifically read:

```text
README.md
pyproject.toml
CHANGELOG.md
ROADMAP.md
ATTRIBUTION.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md
.env.example
prospectiq/constants.py
prospectiq/branding.py
prospectiq/demo.py
prospectiq/cli.py
prospectiq/models/lead.py
prospectiq/enrichment/scoring.py
prospectiq/enrichment/enricher.py
prospectiq/enrichment/email_patterns.py
prospectiq/enrichment/smtp_verify.py
prospectiq/scrapers/registry.py
prospectiq/exporters/csv_exporter.py
.github/workflows/ci.yml
tests/
docs/assets/
```

Also run:

```bash
git status
python -m pytest
ruff check .
ruff format --check .
mypy prospectiq
python -m prospectiq --demo
```

Record current behavior before editing.

Do not rewrite README copy based on assumptions. Verify every important technical claim against the implementation.

---

# 2. Supplied Brand Assets

Two source assets accompany this task.

## Asset A — ProspectIQ Logo

Source image characteristics:

```text
1536 × 1024
white background
centered ProspectIQ emblem + wordmark
teal / dark teal / gold palette
```

It contains:

- the ProspectIQ target/intelligence emblem;
- the ProspectIQ serif wordmark;
- teal emphasis on `IQ`;
- gold radial lines and ornamental details.

This is the canonical visual identity.

Use the visual identity faithfully.

## Asset B — ProspectIQ Cover

Source image characteristics:

```text
1672 × 941
wide cinematic dark layout
deep navy background
teal/cyan data-flow lines
gold signal accents
glass interface cards
high-tech data pipeline presentation
```

It visually communicates:

```text
sources → collect → normalize → enrich → score → structured records
```

This second image is the **primary design reference for the entire README**.

The README should visually inherit:

- deep navy / almost-black backgrounds;
- teal / cyan as the dominant data-flow accent;
- restrained warm gold;
- sharp white typography;
- blue-black glass UI;
- fine connected lines;
- grid geometry;
- glowing nodes;
- radial intelligence rings;
- clean data visualization;
- high-end information-density;
- precise spacing;
- cinematic but controlled contrast.

Do **not** attempt to recreate the README with generic GitHub-blue branding.

---

# 3. Important GitHub README Constraints

The README must be excellent **within GitHub's actual rendering limits**.

GitHub Markdown does not allow us to build a normal web page with unrestricted CSS or JavaScript.

Therefore:

## Do not attempt

- custom JavaScript animations;
- client-side scroll effects;
- custom web fonts loaded through CSS;
- arbitrary `<style>` tags;
- fixed or sticky custom sidebars;
- React components;
- script-based counters;
- externally executed widgets;
- hover animations requiring custom CSS;
- unsupported iframe embeds.

## Use instead

- high-quality static PNG / SVG assets;
- optimized animated GIFs where motion materially improves understanding;
- `<picture>` where useful for light/dark variants;
- semantic HTML supported by GitHub;
- `<details>` and `<summary>` for collapsible technical sections;
- Mermaid only when it renders reliably and adds value;
- custom-designed SVG diagrams for anything that must precisely match the brand;
- anchor links;
- GitHub callouts;
- native Markdown tables;
- compact HTML alignment for hero / badge rows.

The README should never depend on unsupported browser behavior.

---

# 4. Brand System to Implement

Create a README-specific brand system using the cover image as the source of truth.

## Core colors

Use these consistently when producing repository assets:

```text
Canvas / Midnight       #001019
Deep Navy               #0E272F
Structural Navy         #143D49
Glass Teal              #225E6A
Intelligence Teal       #2999A3
Soft Cyan               #9CC6CF
Signal Gold             #C9B171
Brighter Gold Accent    #D6A84B
Soft White              #F5F8FA
Muted Slate             #8FA5B0
```

If a generated asset needs stronger contrast, make small accessibility-safe adjustments while preserving the same identity.

## Visual rules

- Teal/cyan represents data flow, normalization, enrichment, and active system state.
- Gold represents confidence, provenance, checkpoints, important signals, or emphasis.
- White represents primary labels and headings.
- Slate represents metadata and secondary copy.
- Deep navy is the dominant canvas.
- Avoid rainbow UI.
- Avoid neon overload.
- Avoid excessive bloom.
- Avoid generic “hacker terminal” visuals.
- Avoid crypto/web3 visual language.
- Avoid red except for actual warnings/errors.

## Typography

GitHub controls the README body's font, so do not pretend we can globally replace it.

Instead:

- use GitHub-native body typography for readability;
- bake ProspectIQ's branded typography into hero images, section banners, diagrams, and logo assets;
- use concise uppercase tracking in designed assets for labels;
- use serif styling only where it directly reflects the supplied ProspectIQ wordmark;
- keep body text easy to scan.

---

# 5. Truthfulness and Positioning

The README must accurately describe the current product.

ProspectIQ currently:

- collects publicly available profile information from supported sources;
- normalizes source-specific data into a unified lead schema;
- extracts published contact details;
- enriches through public websites and company-domain resolution;
- infers likely email patterns;
- optionally performs SMTP verification;
- calculates a transparent additive `lead_score`;
- exports structured CSV data locally;
- supports an offline fictional-data demo;
- includes typed failures, pacing, and responsible-use controls.

ProspectIQ's documented `lead_score` means:

> how actionable / complete a record is

It does **not** mean:

> likelihood to buy

Do not convert the README into hype.

## Important wording rule

The supplied branding image currently includes the phrase:

```text
AI PROSPECT INTELLIGENCE
```

Do not copy that phrase throughout the README as a technical claim.

The descriptive README copy must remain faithful to the implementation.

Prefer:

```text
Open-Source Lead Intelligence
Public Profile Intelligence
Traceable Contact Enrichment
Public Data → Structured Records
```

Do not add claims such as:

```text
AI-powered scoring
machine-learning prospect prediction
predictive conversion intelligence
autonomous sales agent
AI outreach automation
guaranteed email accuracy
guaranteed deliverability
purchase-intent prediction
```

The README's design may inherit the cover's visual identity; its technical claims must inherit the repository's actual implementation.

---

# 6. Required Asset Structure

Create or normalize this folder:

```text
docs/
└── assets/
    ├── prospectiq-logo-source.png
    ├── prospectiq-cover.png
    ├── prospectiq-logo-dark.png
    ├── prospectiq-logo-mark.png
    ├── prospectiq-readme-hero.png
    ├── prospectiq-pipeline.svg
    ├── prospectiq-pipeline.gif
    ├── prospectiq-demo.gif
    ├── prospectiq-demo.tape
    ├── prospectiq-architecture.svg
    ├── prospectiq-source-map.svg
    ├── prospectiq-score-explainer.svg
    └── prospectiq-social-preview.png
```

Do not create files merely to satisfy this list. Every retained asset must be used.

If an image-processing tool is available, derive optimized assets from the supplied images.

If it is not available, create the required source-file placement instructions in:

```text
docs/README_ASSET_SETUP.md
```

Do not fabricate a replacement for the user's supplied logo.

---

# 7. Hero Section — Highest Priority

The top 700–1000 pixels of the README matter more than everything below them.

When a visitor opens the repository, they should immediately see:

1. premium visual identity;
2. exact product category;
3. concise explanation;
4. project health;
5. direct path to try it.

## Required order

### 7.1 Cover first

Use the supplied cover or an optimized derivative:

```html
<p align="center">
  <img
    src="docs/assets/prospectiq-readme-hero.png"
    alt="ProspectIQ lead-intelligence pipeline visualizing public data collection, normalization, enrichment, scoring, and structured output"
    width="100%"
  />
</p>
```

The hero derivative should retain the dark navy / teal / gold aesthetic.

The cover is the visual centerpiece.

Do not place a giant text heading above it.

### 7.2 Small brand lockup

Below the cover, include a smaller clean ProspectIQ logo treatment.

The logo should reinforce identity, not duplicate the cover at full size.

Target visual width:

```text
380–520 px
```

If the original logo's white background looks visually disconnected from the dark cover, create a polished dark-background derivative using the existing emblem/wordmark rather than placing a raw white rectangle under the hero.

Preserve the original logo as a source asset.

### 7.3 Value proposition

Use a concise statement:

```text
Open-source lead intelligence for turning fragmented public-profile data into structured, traceable, locally controlled records.
```

### 7.4 Pipeline line

Immediately below:

```text
Collect → Normalize → Enrich → Score → Export
```

Style this as either:

- a small custom SVG strip; or
- centered text with subtle separators.

Do not overdecorate it.

### 7.5 Proof / status badges

Use no more than 6 primary badges.

Recommended:

- CI
- Python 3.10+
- MIT
- Version
- Typed
- Ruff / lint

All badges must visually align with ProspectIQ colors.

Do not add meaningless badges.

### 7.6 Primary navigation row

Create a compact centered navigation row:

```text
Quick Start · Demo · How It Works · Sources · Architecture · Responsible Use
```

Each item must link to a valid README anchor.

---

# 8. README Information Architecture

Rebuild the README in this exact high-level order unless repository facts require a small correction.

```text
Hero
Fast Start
Why ProspectIQ
Animated Pipeline
Core Capabilities
Live Demo
Supported Sources
How Enrichment Works
Scoring & Provenance
Architecture
Output Schema
CLI Reference
Configuration
Responsible Use
Testing & Quality
Extending ProspectIQ
Roadmap
Contributing
Security
Attribution
License
Maintainer
```

The README should be comprehensive, but **progressively disclose complexity**.

The top half should answer:

```text
What is it?
Why should I care?
How do I run it?
What does it do?
Can I trust what I am seeing?
```

The lower half should answer:

```text
How is it built?
How do I configure it?
How do I contribute?
What are the safeguards?
```

---

# 9. Fast Start — Make First Use Effortless

This section should appear immediately after the hero.

Title:

```md
## Start in 60 Seconds
```

Provide the shortest correct path.

Example structure:

```bash
git clone https://github.com/davishiggins/prospectiq.git
cd prospectiq
python -m venv .venv
```

Then show platform-specific activation compactly.

Use tabs only if GitHub genuinely supports the chosen implementation. Otherwise use `<details>` blocks:

```html
<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
source .venv/bin/activate
pip install -e .
prospectiq --demo
```

</details>
```

and Windows separately.

The easiest first experience is:

```bash
prospectiq --demo
```

Make it visually obvious that:

- it uses fictional data;
- it needs no credentials;
- it needs no live network;
- it demonstrates the real pipeline.

Add one sentence:

> New here? Run the offline demo first. It is the fastest way to understand ProspectIQ without configuring a source.

---

# 10. Why ProspectIQ — Make the Value Clear

Rewrite the existing “Why ProspectIQ” section into a concise product explanation.

Do not attack commercial tools.

Position the project around:

### Transparency

Every selected email candidate carries provenance and confidence metadata.

### Local control

Exports stay on the user's machine rather than being automatically stored in a hosted vendor database.

### Inspectable scoring

The record score is additive and documented rather than opaque.

### Extensibility

A source is implemented as a module plus a registry entry.

### Responsible scope

ProspectIQ intentionally does not bypass CAPTCHAs, scrape private data, or send mass outreach.

Use a premium comparison table, but keep it factual.

---

# 11. Animated Pipeline — Signature README Element

Create one elegant, subtle, high-quality animation that explains ProspectIQ in under 8 seconds.

Output:

```text
docs/assets/prospectiq-pipeline.gif
```

Target:

```text
1400–1600 px wide
5–8 second seamless loop
under ~3 MB if practical
dark navy background
```

Animation stages:

```text
PUBLIC SOURCES
      ↓
COLLECT
      ↓
NORMALIZE
      ↓
ENRICH
      ↓
SCORE
      ↓
EXPORT
```

Visual treatment:

- use the second supplied cover image as inspiration;
- thin teal streams move left-to-right;
- a gold checkpoint pulse passes through stages;
- abstract source cards feed the pipeline;
- data becomes progressively more structured;
- final output resolves into a clean record / CSV grid;
- background uses subtle grid lines and radial geometry;
- keep motion refined and slow enough to understand.

Do not animate everything at once.

Do not use flashing effects.

Do not fake performance metrics.

Do not use real people's contact data.

### Accessibility

Directly beneath the animation include a text explanation so the README remains understandable without motion.

---

# 12. Real Terminal Demo Animation

Create a second animation showing actual ProspectIQ usage.

Use:

```text
prospectiq --demo
```

Never use a real collection run in public marketing assets.

Create:

```text
docs/assets/prospectiq-demo.tape
docs/assets/prospectiq-demo.gif
```

Preferred tool:

```text
VHS
```

Fallback:

```text
asciinema + agg
```

Fallback 2:

```text
real static screenshot
```

Recommended terminal styling:

```text
dark navy background
JetBrains Mono / Cascadia Code / Fira Code
teal primary output
gold warnings / metadata
soft white text
```

Do not add fake command output.

Do not display:

- `.env`;
- cookies;
- API keys;
- proxy URLs;
- local username paths;
- real names/emails/phone numbers from live collection.

Add the real demo GIF inside a section:

```md
## See ProspectIQ Run
```

with a one-line explanation.

After this exists, delete:

```text
docs/assets/prospectiq-demo-placeholder.md
```

The repository currently has only this placeholder; the finished README should not.

---

# 13. Core Capabilities — Design as a Premium Grid

Do not use one huge bullet list.

Create a clean visual capability matrix.

Preferred groups:

## Collect

```text
8 supported sources
one source interface
conservative pacing
typed network failures
```

## Normalize

```text
one Lead model
alias mapping
type coercion
source-specific extras preserved
```

## Enrich

```text
published website data
company-domain resolution
email pattern evidence
optional SMTP checks
optional Hunter.io coverage
```

## Score & Export

```text
transparent additive score
email provenance
stable CSV schema
formula-injection protection
local export
```

Use either:

- a custom 2×2 SVG card grid matching the cover design; or
- a Markdown / HTML two-column presentation that remains readable on mobile.

Do not make the README depend on tiny text embedded in raster images.

---

# 14. Supported Sources — Make It Easier to Scan

The current large table is useful but visually dense.

Create a source overview asset:

```text
docs/assets/prospectiq-source-map.svg
```

It should show the eight actual source categories:

```text
Instagram
TikTok
LinkedIn
GitHub
YouTube
Twitch
Pinterest
Link-in-bio
```

Use neutral platform labels or simple generic icons unless a trademark-safe icon source is already used.

Do not imply partnership with these services.

Under the visual strip, preserve the detailed source table.

Improve the table's columns to emphasize:

```text
Source
Auth
Best For
Primary Fields
Limitations
```

If the table becomes too wide, place detailed fields inside a `<details>` element.

---

# 15. How Enrichment Works — Explain the Real Logic

Create a visually clear stage-by-stage explanation based on the implementation.

Use the real process:

1. Bio extraction
2. Website deep-scrape
3. Company-domain resolution
4. Pattern inference
5. Optional SMTP probing
6. Optional Hunter.io enrichment
7. Candidate selection

Add a custom diagram or compact ordered list.

Important copy:

> ProspectIQ does not treat every discovered email equally. Candidate source, corroboration, verification behavior, and provenance determine which address is selected.

Keep the existing caveat that SMTP checks are imperfect.

Do not imply verification guarantees deliverability.

---

# 16. Scoring and Provenance — Make Trust a Feature

This should become one of the strongest sections of the README.

Use a designed visual:

```text
docs/assets/prospectiq-score-explainer.svg
```

The visual should communicate:

```text
record completeness → transparent score
email candidate → source + confidence + verification state
```

Required textual clarification:

> `lead_score` measures how complete and actionable a record is. It does not predict whether a person will buy.

Show the scoring table.

Show the provenance fields:

```text
email
email_source
email_confidence
email_verified
```

Explain:

- observed address;
- inferred address;
- verified state;
- unconfirmed state.

Make it impossible for a reader to confuse scoring with predictive sales AI.

---

# 17. Architecture — Replace the Generic Look

The existing Mermaid diagram is functional but visually basic.

Create:

```text
docs/assets/prospectiq-architecture.svg
```

Style it directly from the supplied cover:

```text
dark navy canvas
teal connectors
gold boundary/checkpoint nodes
glass-like module cards
white module labels
```

Show:

```text
CLI
  ↓
Source Registry
  ↓
Scrapers
  ↓
Lead.from_raw()
  ↓
Enrichment
  ↓
Candidate Selection
  ↓
Scoring
  ↓
CSV Export
```

Below the visual, keep the actual package tree and the important architecture explanation.

Make these two design decisions prominent:

1. `Lead.from_raw()` is the normalization boundary.
2. `scrapers/registry.py` is the authoritative source registry.

Use a two-card “Design Decisions” presentation if it renders cleanly.

---

# 18. Output Schema — Keep the README Clean

Do not force every casual user to scroll through a massive schema table before getting to other important information.

Use:

```html
<details>
<summary><strong>View the full CSV schema</strong></summary>
...
</details>
```

Before the collapsed table show a concise sample:

```text
source
username
display_name
profile_url
website
email
email_source
email_confidence
email_verified
company
company_domain
lead_score
collected_at
```

Mention source-specific fields are appended without destroying the unified core schema.

Preserve the formula-injection protection explanation.

---

# 19. CLI Reference — Progressive Disclosure

Keep Quick Start easy.

Move the full CLI reference lower.

Use collapsible groups:

```text
Collection
Sources
Exports
Doctor
Global flags
```

Example:

```html
<details>
<summary><code>prospectiq collect</code></summary>

...
</details>
```

Ensure every command shown still matches actual `--help`.

Do not invent flags.

---

# 20. Configuration — Improve Usability

Keep every supported environment variable.

Split the current table into:

### Most users need nothing

Explain that demo and several sources work without configuration.

### Optional authentication / enrichment

```text
PROSPECTIQ_LINKEDIN_COOKIE
PROSPECTIQ_HUNTER_API_KEY
```

### Network behavior

```text
PROSPECTIQ_DELAY_MIN
PROSPECTIQ_DELAY_MAX
PROSPECTIQ_PROXY
PROSPECTIQ_PROXY_FILE
PROSPECTIQ_FREE_PROXY
```

### Output / behavior

```text
PROSPECTIQ_OUTPUT_DIR
PROSPECTIQ_SMTP_VERIFY
PROSPECTIQ_UPDATE_CHECK
NO_COLOR
```

Keep the LinkedIn cookie warning prominent.

Do not make authentication setup look mandatory when it is not.

---

# 21. Responsible Use — Premium, Visible, Serious

Do not bury this at the very bottom.

Add a small early callout near Quick Start:

```md
> [!IMPORTANT]
> ProspectIQ works with publicly available information. You remain responsible for lawful collection, platform terms, secure handling, deletion requests, and compliant outreach.
```

Keep the full Responsible Use section later.

Visually separate:

## You are responsible for

- applicable law;
- platform terms;
- rate limits;
- authorized access;
- secure handling;
- deletion / opt-out obligations;
- lawful outreach.

## ProspectIQ deliberately does not do

- CAPTCHA bypass;
- stealth fingerprint evasion;
- credential harvesting;
- account takeover;
- private/paywalled data access;
- mass-message sending.

This section should feel like intentional product design, not defensive fine print.

---

# 22. Testing & Engineering Quality — Surface the Proof

The README should clearly show that ProspectIQ is engineered, not merely scripted.

Highlight:

```text
Python 3.10–3.12 CI
pytest
hermetic test design
HTTP mocking
SMTP hard-blocking during tests
Ruff
mypy
CLI smoke tests
formula-injection protection
typed errors
```

If the exact test count can be verified from a fresh run, it may be displayed.

If it cannot be verified, do not hard-code a number.

Never use stale test counts.

Add a concise verification block:

```bash
pytest
ruff check .
ruff format --check .
mypy prospectiq
```

---

# 23. README Navigation / Table of Contents

Create an elegant compact table of contents after the hero or Quick Start.

Do not make it enormous.

Recommended:

```text
Getting Started
- Quick Start
- Demo
- Supported Sources

How It Works
- Pipeline
- Enrichment
- Scoring
- Architecture

Reference
- CLI
- Configuration
- Output Schema

Project
- Responsible Use
- Testing
- Roadmap
- Contributing
```

Use standard anchor links.

GitHub does not support a custom sticky sidebar here; do not attempt one.

---

# 24. Visual Section Dividers

Create a reusable lightweight section-divider asset only if it materially improves the README.

Example design:

```text
thin teal line — small gold diamond — thin teal line
```

Do not insert giant decorative images between every section.

Use dividers sparingly:

- before “How It Works”;
- before “Architecture”;
- before “Responsible Use”;
- before contributor/project metadata.

The README should feel premium, not theatrical.

---

# 25. Light / Dark Theme Strategy

The primary cover is dark and should work in both GitHub themes.

For smaller diagrams:

- ensure dark assets have an intentional frame;
- use soft white internal text;
- maintain adequate contrast;
- do not rely on GitHub page background for legibility.

For the white logo:

- preserve the original source;
- create a dark README derivative if possible;
- use `<picture>` only if a true light/dark pair exists.

Do not fake a light/dark implementation with broken files.

---

# 26. Performance Requirements

A high-quality README must also load quickly.

Targets:

```text
hero: ideally < 1.5 MB
each SVG: typically < 250 KB
pipeline GIF: ideally < 3 MB
demo GIF: ideally < 4 MB
total README-specific assets: keep reasonable
```

Use:

```text
pngquant
oxipng
gifsicle
svgo
Pillow
```

where available.

Do not sacrifice visible quality for tiny file size, but remove obvious waste.

No 20–50 MB GIFs.

No unoptimized generated artwork.

---

# 27. Accessibility Requirements

Every image must have meaningful alt text.

Do not use:

```text
alt="image"
alt="logo"
alt="screenshot"
```

Use descriptions of purpose.

Animation must not flash.

Important information shown in an image must also exist as text.

Use logical heading levels.

Do not skip from `##` to `####` without reason.

Do not communicate success / warning solely through color.

Do not center-align long body text.

Keep tables readable.

---

# 28. Mobile Requirements

Inspect the README at a narrow width.

The finished README must avoid:

- gigantic fixed-width images;
- multi-column HTML that becomes unreadable;
- oversized tables before the user reaches Quick Start;
- tiny text baked into images;
- horizontal scrolling caused by decorative HTML;
- badge rows that become visually chaotic.

Prefer `width="100%"` for hero visuals.

Use smaller fixed widths only for logos / marks.

---

# 29. Exact README Opening Structure

Use this as the structural target.

Do not blindly paste it without adapting paths and verified facts.

```md
<p align="center">
  <img
    src="docs/assets/prospectiq-readme-hero.png"
    alt="ProspectIQ visualizing its collect, normalize, enrich, score, and export pipeline"
    width="100%"
  />
</p>

<p align="center">
  <img
    src="docs/assets/prospectiq-logo-dark.png"
    alt="ProspectIQ"
    width="460"
  />
</p>

<p align="center">
  <strong>Open-source lead intelligence for turning fragmented public-profile data into structured, traceable, locally controlled records.</strong>
</p>

<p align="center">
  Collect → Normalize → Enrich → Score → Export
</p>

<p align="center">
  <!-- 4–6 carefully selected badges -->
</p>

<p align="center">
  <a href="#start-in-60-seconds">Quick Start</a>
  ·
  <a href="#see-prospectiq-run">Demo</a>
  ·
  <a href="#how-it-works">How It Works</a>
  ·
  <a href="#supported-sources">Sources</a>
  ·
  <a href="#architecture">Architecture</a>
  ·
  <a href="#responsible-use">Responsible Use</a>
</p>
```

Immediately after:

```md
## Start in 60 Seconds
```

The user should not have to scroll through several marketing sections before seeing how to run the project.

---

# 30. Suggested Main README Copy

Use this as the opening product description unless repository inspection reveals something more precise.

```md
ProspectIQ is an open-source Python lead-intelligence pipeline built around transparency.

It collects publicly available profile information from supported sources, normalizes source-specific fields into one consistent lead model, enriches records using published websites and company-domain signals, evaluates record actionability with documented rules, and exports a stable CSV locally.

The goal is not to hide the process behind an opaque score. ProspectIQ keeps provenance visible so you can distinguish what was observed, what was inferred, and what remains unverified.
```

Then:

```md
> [!NOTE]
> `lead_score` measures record completeness and actionability. It is not a prediction of purchase intent.
```

---

# 31. Use the Cover Design Intelligently

The supplied cover image is a visual brand reference, not a literal product screenshot.

Do not treat every visual element inside it as a real application feature.

Examples of cover artwork that must not automatically become README claims:

- fictional lead cards;
- arbitrary score values;
- “high intent” labels;
- fake company profiles;
- fictional conversion analytics;
- visual platform labels not actually supported by the repository.

Instead, inherit:

- color;
- lighting;
- grid structure;
- data-flow design;
- glass panel language;
- line work;
- composition;
- data-transformation storytelling.

Public README factual claims must come from the codebase.

---

# 32. Do Not Overdesign the README

World-class does not mean “maximum visual noise.”

Avoid:

- 30 badges;
- emoji on every header;
- giant ASCII art;
- rainbow gradients;
- full-width visual assets for trivial sections;
- repeating the logo every few screens;
- fake dashboards;
- huge blocks of centered copy;
- overlong animations;
- unnecessary SVG ornaments;
- sections that look good but make information harder to find.

The ideal visual rhythm is:

```text
major visual
concise copy
useful command
visual explanation
technical detail
breathing room
```

---

# 33. README Footer / Maintainer Presentation

End the README cleanly.

Include:

```text
Maintainer
Davis Higgins
Portfolio
Higgins Digital
GitHub
```

Keep the existing project attribution.

Use this lineage wording if consistent with `ATTRIBUTION.md`:

> ProspectIQ is a substantially re-architected and independently maintained derivative of the MIT-licensed Scout project. See `ATTRIBUTION.md` for inherited functionality and rewritten components.

Do not hide upstream attribution.

---

# 34. Optional Documentation Extraction

If the redesigned README remains excessively long after progressive disclosure, you may create:

```text
docs/CLI.md
docs/CONFIGURATION.md
docs/SCORING.md
docs/ARCHITECTURE.md
```

Only do this if it improves navigation.

The README should remain self-sufficient for:

- understanding the project;
- installing it;
- running demo mode;
- collecting data;
- understanding enrichment;
- understanding the score;
- finding safety guidance.

Do not move essential onboarding out of the README.

---

# 35. Repository Metadata Alignment

Inspect the current:

```text
pyproject.toml
ProspectIQ GitHub About description
README tagline
prospectiq/constants.py
```

Do not let these tell four different stories.

Recommended canonical description:

```text
Open-source lead intelligence that turns public profiles into structured, traceable, locally controlled records.
```

Recommended repository topics:

```text
python
lead-intelligence
contact-enrichment
public-data
data-pipeline
data-normalization
cli
open-source
pytest
github-actions
```

Only modify repository metadata if authenticated access and user intent allow it.

Otherwise document the exact manual change.

---

# 36. Social Preview

Create:

```text
docs/assets/prospectiq-social-preview.png
```

Target:

```text
1280 × 640
```

Use the supplied cover design.

Requirements:

- ProspectIQ mark readable at thumbnail size;
- dark navy canvas;
- teal data-flow lines;
- gold accents;
- minimal text;
- no fake metrics;
- no personal contact data.

Manual GitHub step if needed:

```text
Repository → Settings → General → Social preview → Edit → Upload image
```

Document this in:

```text
docs/README_ASSET_SETUP.md
```

if Claude cannot upload it.

---

# 37. Asset Generation Scripts

Where useful, create reproducible scripts rather than one-off hand-edited output.

Recommended:

```text
scripts/readme/
├── build_pipeline_animation.py
├── build_architecture_svg.py
├── optimize_assets.py
└── prospectiq-demo.tape
```

Scripts should:

- use only local source assets;
- not call paid APIs;
- not fetch personal data;
- be deterministic where practical;
- have concise instructions.

Do not create a large asset-generation framework.

---

# 38. Verification

Before declaring completion, run:

```bash
python -m pytest
ruff check .
ruff format --check .
mypy prospectiq
python -m prospectiq --demo
```

If README-only changes truly do not affect code, tests should remain green.

Then inspect:

```text
README.md
```

for:

- broken anchors;
- broken relative asset paths;
- broken HTML;
- missing images;
- duplicate headings;
- invalid badge links;
- incorrect commands;
- stale version values;
- unsupported claims;
- incorrect source names.

If possible, render the README through:

- GitHub preview;
- VS Code Markdown preview;
- a local GitHub-flavored Markdown renderer.

The final visual review should include:

```text
desktop wide
desktop narrow
mobile-width approximation
GitHub light theme
GitHub dark theme
```

---

# 39. Specific Acceptance Criteria

The task is not complete until all of the following are true.

## Hero

- [ ] Supplied ProspectIQ cover branding is implemented.
- [ ] ProspectIQ logo is visibly used.
- [ ] Hero looks premium and intentional.
- [ ] Value proposition is understandable in under 10 seconds.
- [ ] CTA/navigation links work.
- [ ] Badge row is clean and restrained.

## Ease of use

- [ ] `prospectiq --demo` is surfaced near the top.
- [ ] First-time setup is obvious.
- [ ] Windows and macOS/Linux activation instructions are clear.
- [ ] Long technical reference is progressively disclosed.
- [ ] Table of contents / anchors work.

## Visual quality

- [ ] README clearly matches the supplied dark navy / teal / gold cover.
- [ ] Typography inside designed assets matches the brand.
- [ ] Section diagrams share one visual system.
- [ ] Animation is smooth and purposeful.
- [ ] No generic template aesthetic remains.
- [ ] No visual clutter or badge spam.

## Technical accuracy

- [ ] Supported sources are accurate.
- [ ] CLI commands match actual `--help`.
- [ ] Score explanation matches implementation.
- [ ] SMTP caveats remain.
- [ ] Output schema matches implementation.
- [ ] No invented capabilities appear.
- [ ] No fake metrics appear.

## Responsible use

- [ ] Early responsible-use notice exists.
- [ ] Full responsible-use section remains.
- [ ] CAPTCHA bypass is explicitly outside scope.
- [ ] Mass messaging is explicitly outside scope.
- [ ] Private/paywalled data is outside scope.
- [ ] Attribution remains visible.

## Assets

- [ ] Cover optimized.
- [ ] Logo optimized.
- [ ] Pipeline visual exists.
- [ ] Pipeline animation exists if toolchain permits.
- [ ] Demo GIF exists or exact manual fallback is documented.
- [ ] Architecture visual exists.
- [ ] Social preview exists.
- [ ] Placeholder demo document is removed after replacement.
- [ ] All image alt text is meaningful.

## Quality

- [ ] Tests pass.
- [ ] Ruff passes.
- [ ] Formatting check passes.
- [ ] mypy passes.
- [ ] Demo still runs.
- [ ] README rendering has been visually inspected.
- [ ] No secrets or real lead data entered the repository.

---

# 40. Final Report Required

When finished, provide a detailed implementation report containing:

## README

- sections added;
- sections reordered;
- sections collapsed;
- copy rewritten;
- navigation changes;
- onboarding improvements.

## Branding

- exact palette used;
- logo treatment;
- cover implementation;
- typography strategy;
- diagrams created;
- animation created.

## Assets

List every file created, changed, deleted, and optimized.

For each image provide:

```text
dimensions
format
file size
purpose
```

## Developer experience

Explain how setup and first use became easier.

## Accuracy

List technical claims that were verified against code.

List any marketing wording that was deliberately avoided because it would overstate the implementation.

## Verification

Report exact results of:

```text
pytest
ruff
format check
mypy
demo
README link / asset validation
```

## Manual steps

Only include steps Claude genuinely cannot complete.

Do not finish with “README improved successfully.”

Provide evidence.

---

# 41. Final Design Principle

Use this rule throughout the implementation:

> **ProspectIQ should look as precise as the system it describes.**

Every visual element should reinforce one of these ideas:

```text
traceability
transformation
structure
provenance
clarity
control
```

The finished README should feel like a high-end technical product presentation with the usability of excellent open-source documentation.

It should be visually impressive enough to stop someone scrolling, but clear enough that they can install and understand ProspectIQ immediately.

That balance is the definition of success.
