# KISS Résumé 💋 (Keep It Super Simple)

Author your own résumé in a simple Markdown format, run `resume` and get a well formatted, accessible PDF. 

Easily maintain your résumé and generate new versions automatically by making `resume` part of your workflow.

Pipeline: **Markdown → HTML → PDF** (via [WeasyPrint](https://weasyprint.org)).

<a href="docs/resume.pdf"><img src="docs/example-preview.png" alt="Example résumé PDF generated from the included resume.md with default settings" width="420"></a>

See an [example](docs/resume.md) résumé and the [generated output](docs/resume.pdf). 

## Install & run

Requires [uv](https://docs.astral.sh/uv/) and Pango (with its friends: harfbuzz, fontconfig, glib) available from Homebrew.

```bash
uv sync                # create venv, install deps (incl. dev tools)
brew install pango                # install system libs
uv run resume                       # -> resume.pdf, from the current dir
uv run resume --out "Resume.pdf"
uv run resume --md resume.md --css style.css --config config.yaml --out out.pdf
```

Install globally as a `resume` command on PATH:

```bash
uv tool install .                    # then `resume` works anywhere
resume --md ~/resumes/resume.md --out ~/Desktop/Resume.pdf
```

### Files

| File          | Role                                                            |
|---------------|-----------------------------------------------------------------|
| `resume.md`   | **Content.** Frontmatter (name/contact) + Markdown body.        |
| `style.css`   | **Presentation.** All visual styling; values come from `config.yaml`. |
| `config.yaml` | **Knobs.** Page size, margins, fonts, sizes, spacing, bullets.  |
| `resume/`     | The pipeline (a `uv`-installed package). Reads the three files, writes the PDF. Bundles a default `style.css`/`config.yaml` (`resume/data/`) used when a directory has only a `resume.md`. |

All inputs and the output PDF default to the **current working directory**. `style.css`/`config.yaml` fall back to the tool's bundled defaults when a directory has none of its own — drop your own copies next to `resume.md` (or pass `--css`/`--config`) to override.

### macOS note: don't use the system Python

`resume` sets `DYLD_LIBRARY_PATH` in-process so WeasyPrint can find Homebrew's Pango/glib dylibs (which aren't on `dlopen`'s default search path). This only works with non-SIP-protected interpreters — the ones `uv` uses. The system `/usr/bin/python3` is SIP-protected and strips `DYLD_*` vars, so pointing `uv` at it will leave WeasyPrint unable to find its native libs. Stick with `uv`'s default interpreter.

## Markdown conventions

Heading levels map to the résumé structure:

| Markdown | Element                | Example                          |
|----------|------------------------|----------------------------------|
| `#`      | H1 — section header (UPPERCASE) | `# Summary`, `# Experience` |
| `##`     | H2 — role / entry      | `## Engineering Manager`         |
| `###`    | H3 — sub-heading       | `### Achievements`               |
| `*…*`    | meta line (italic): company \| dates \| location | `*Acme Systems \| Mar 2021 - Present \| Portland, USA*` |
| `- `     | bullet                 | `- Grew the team from 4 to 12 engineers …` |
| body text| paragraph (summary, role blurb) | `Engineering leader with 12+ years …` |
| `[text](url)` | link (works in the body *and* in a `contact:` line) | `[github.com/samrivera](https://github.com/samrivera)` |

A line that is *only* italic (`*…*`) is detected as a **meta line** and styled accordingly. Italic used mid-sentence stays normal emphasis.

### Links

Standard Markdown link syntax, `[text](url)`, works both in the body and in
a `contact:` line.

Link color and underline are configurable via `--link-color` / `--link-decoration` in `config.yaml` (`style:` block) — they default to the surrounding text color and `underline`, not the browser-default blue.

### Page breaks

Insert an HTML comment on its own line where a new page should start:

```markdown
<!-- break -->
```

`<!-- pagebreak -->` and `<!-- newpage -->` work too. Each one forces the following content onto a new page (`break-before: page`). The current résumé uses one, before the earliest role, to demonstrate splitting experience across pages.

### Build date

Every page gets the build date (e.g. `July 1, 2026`) printed in small light-gray type in the bottom-right page margin, using the document's own font. It lives in a `@page` margin box, so in the tagged PDF/UA-1 output it's marked as an **artifact** rather than content — screen readers skip it and it doesn't pollute the structure tree or copied text.

```bash
# Pass `--no-date` to omit the date display
uv run resume --no-date
```

The footer's font-family is injected as a literal into `@page` (from `--font-family` in `config.yaml`, falling back to the bundled default) because WeasyPrint resolves neither `var()` nor body inheritance inside `@page`. Its size and color are fixed at `7.5pt` / `#b3b3b3` and aren't currently configurable.

## Customizing the look

Copy `resume/data/config.yaml` next to your `resume.md` and edit that as necessary. Local files will override  the bundled default. Everything under `style:` is injected as a CSS custom property, so you can retune without touching `style.css`. Common changes:

```yaml
page:
  size: "595pt 842pt"      # A4 instead of US Letter
  margin: "40pt 50pt 40pt 50pt"

style:
  "--font-family": '"Helvetica Neue", Helvetica, Arial, sans-serif'
  "--base-size": "10.5pt"
  "--line-height": "13.5pt"
  "--h1-transform": "none"     # stop upper-casing section headers
  "--bullet-char": '"\2022"'   # smaller round bullet (• )
```

For structural style changes (new selectors, borders, two-column, etc.) edit `style.css` directly. The `@page` rule (size + margins) is generated by `resume.builder` from `config.yaml`, because WeasyPrint does not resolve `var()` inside `@page`.

## PDF/UA-1
The output is a tagged **PDF/UA-1** — the ISO standard (14289-1) for accessible PDF. Rather than just painting text at fixed positions on the page, the PDF carries a structure tree marking what's a heading, a paragraph, or a list item, along with reading order and language metadata. That's the same structure screen readers rely on to navigate the document by section. Text copied from these PDFs will reflows by paragraph instead of breaking at every visual line.

### Copy/paste & résumé parsers (ATS)

Not every tool reads the structure tree — macOS Preview's copy/paste and most ATS parsers (Workday, Greenhouse, …) read the PDF's raw content stream in paint order instead. The stylesheet is written so that both audiences get clean text:

- Bullet markers are part of normal inline flow (never absolutely positioned — positioned elements are painted in a later pass, which would scramble the content stream and make parsers read list items out of order, after the following section). Each item extracts on its own line as `● Grew the team …`, in document order, with a real separator space after the marker. `tests/test_pdf_extraction.py` guards this.
- The marker character is real text, so it's exactly what pasting and parsing produce. Prefer `- ` prefixes in extracted text? Set `--bullet-char: '"\2013"'` (en dash) or `'"-"'` in `config.yaml` — the trade-off is that the printed bullet changes too; a PDF can't render `●` but copy as `-` (that would need `ActualText`, which WeasyPrint doesn't emit).
- Line breaks *within* a wrapped paragraph are up to the extractor: tag-aware tools (Acrobat, Word) reflow by paragraph; geometry-based ones (Preview, `pdftotext`) still break at every visual line. That part is the viewer, not the PDF.
- For ATS uploads, consider `--no-date` so a parser can't mistake the build-date footer for résumé content (tag-aware parsers already skip it as an artifact).

## Notes on fonts & fidelity

This pipeline defaults to a Helvetica-compatible stack (`Nimbus Sans` / `Liberation Sans` on Linux). For a pixel match to Helvetica Neue, run on a machine that has it installed and set `--font-family` accordingly. WeasyPrint will embed whatever it resolves at build time, so the PDF renders identically everywhere afterward.
