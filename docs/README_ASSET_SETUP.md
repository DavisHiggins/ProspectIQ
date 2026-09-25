# ProspectIQ README asset workflow

All generated README visuals are reproducible and stay inside the repository.
The generator makes no network requests and the demo capture uses only the
fictional records built into `prospectiq/demo.py`.

## Build the current asset set

From the repository root:

```bash
python scripts/readme/build_readme_assets.py
python scripts/readme/validate_readme.py
```

The first command rebuilds the pipeline, architecture, source, scoring, hero,
social-preview, and terminal-demo assets. The second checks README anchors,
relative links, image paths, dimensions, and asset size budgets.

## Canonical logo and cover source files

The task specification describes two supplied images, but neither source file
was present in this repository snapshot when the asset workflow was created.
Do not substitute or redraw the logo.

One manual source-placement step remains:

1. Copy the supplied 1536 × 1024 logo to
   `docs/assets/prospectiq-logo-source.png`.
2. Copy the supplied 1672 × 941 cover to
   `docs/assets/prospectiq-cover.png`.
3. Run `python scripts/readme/build_readme_assets.py` again.

When those files exist, the generator optimizes the sources, creates
`prospectiq-logo-dark.png` from the actual logo, and uses the actual cover as
the base for the README hero and social preview. The source images remain in
the repository so future derivatives can always be traced to the originals.

After the canonical logo derivative exists, replace the temporary text lockup
below the hero in `README.md` with:

```html
<p align="center">
  <img
    src="docs/assets/prospectiq-logo-dark.png"
    alt="ProspectIQ target-intelligence emblem and wordmark"
    width="460"
  />
</p>
```

## GitHub social preview

The generated preview is `docs/assets/prospectiq-social-preview.png` at
1280 × 640. Uploading it changes repository settings and cannot be completed
from a source snapshot without authenticated repository administration:

```text
Repository → Settings → General → Social preview → Edit → Upload image
```

## GitHub About metadata

The repository About description and topics were aligned through authenticated
GitHub CLI access on 2026-09-25:

```text
Description
Open-source lead intelligence that turns public profiles into structured, traceable, locally controlled records.

Topics
python, lead-intelligence, contact-enrichment, public-data, data-pipeline,
data-normalization, cli, open-source, pytest, github-actions
```

## Terminal capture

`docs/assets/prospectiq-demo.gif` is generated from a real local run of:

```bash
python -m prospectiq --demo --no-color
```

The generator shortens the absolute output path and replaces the variable
timestamp in the filename. It does not add capabilities, records, scores, or
command output. `docs/assets/prospectiq-demo.tape` is retained as an equivalent
VHS recipe for maintainers who prefer that tool.
