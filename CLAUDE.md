# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Markdown → PDF resume builder: `resume.md` (content) + `style.css` (presentation) + `config.yaml` (knobs) → a tagged **PDF/UA-1** via WeasyPrint. Tagged output matters because it makes copy/paste reflow by paragraph instead of breaking at every visual line — don't drop `pdf_variant="pdf/ua-1"` without a reason.

## Commands

```bash
uv sync                    # install deps + dev tools (mypy, pyright, pytest, ruff)
uv run resume               # build resume.pdf from cwd's resume.md (+ style.css/config.yaml, or the bundled defaults)
uv run resume --md resume.md --css style.css --config config.yaml --out out.pdf

./scripts/check.sh          # full gate: ruff format --check, ruff check, pytest, mypy, pyright
./scripts/check.sh --fix    # apply ruff format + ruff check --fix, then run the gate
./scripts/fix.sh            # just the auto-fixes (ruff format + ruff check --fix)

uv run pytest                              # all tests
uv run pytest tests/test_builder.py::test_build_css_uses_defaults_when_page_missing  # single test
uv run mypy
uv run pyright
```

Run `./scripts/check.sh` before considering any change to `resume/` done — it's the single source of truth for green (format + lint + tests + both type checkers).

On macOS, WeasyPrint loads Pango/glib via `cffi.dlopen` by bare soname, which can't find Homebrew's dylibs because `/opt/homebrew/lib` (Apple Silicon) and `/usr/local/lib` (Intel) aren't in dlopen's default search path. `resume/builder.py::_ensure_dyld_lib_path` handles this automatically — it prepends the existing Homebrew lib dir to `DYLD_LIBRARY_PATH` in-process, right before the lazy `weasyprint` import inside `build_resume`. So `uv run resume` just works. Only relevant for commands that actually render a PDF; lint/type/test don't import WeasyPrint.

## Architecture

Three-file separation is the core design, enforced by convention rather than code:

- **`resume.md`** — content only. YAML frontmatter (`name`, `contact`) + a Markdown body.
- **`style.css`** — presentation only, expressed entirely through `var(--custom-property, fallback)` so it never needs editing for a retune.
- **`config.yaml`** — knobs. Everything under `style:` in this file is injected verbatim as CSS custom properties on `:root`; `page:` (size/margin) becomes the `@page` rule. `resume/builder.py` generates `@page` from config rather than letting `style.css` reference `var()` inside `@page`, because WeasyPrint doesn't resolve custom properties there.

`resume/builder.py` is the whole pipeline and is small enough to read in one pass:
1. `split_frontmatter` — pulls the leading `---` YAML block off `resume.md`.
2. `render_body_html` — Markdown → HTML via `python-markdown` (`extra`, `sane_lists`). Page-break markers (`<!-- break -->`, `<!-- pagebreak -->`, `<!-- newpage -->`) are regex-substituted for a `<div class="pagebreak">` *before* Markdown conversion. A paragraph that is *only* an italic run (`<p><em>...</em></p>`) is promoted to `<p class="meta">` after conversion — this is how "company | dates | location" lines get their distinct styling; inline italics mid-sentence are untouched.
3. `render_header_html` — turns frontmatter `name`/`contact` into HTML (contact may be a string or a list).
4. `build_css` — concatenates the generated `@page` rule, a `:root { --k: v; }` block from `config["style"]`, and the raw `style.css`. When given `date_text` (the default path — CLI opt-out via `--no-date`), the `@page` rule also gets a `@bottom-right` margin box with the build date in small light-gray type; the font-family is injected as a literal (from `config["style"]["--font-family"]`, falling back to `DEFAULT_FONT_FAMILY`, which must stay in sync with the `body` fallback stack in `style.css`) because WeasyPrint resolves neither `var()` nor body inheritance inside `@page`.
5. `build_resume` — assembles the full HTML document and calls WeasyPrint's `HTML(...).write_pdf(..., pdf_variant="pdf/ua-1")`. The output is always a tagged PDF/UA-1 (there is no opt-out).

Markdown heading levels map directly to resume structure and both `resume/builder.py` and `style.css` encode this same mapping in comments — keep them in sync if it changes:

| Markdown | Meaning |
|---|---|
| `#` (H1) | section header (Summary, Experience, ...), uppercased by default |
| `##` (H2) | role / entry title |
| `###` (H3) | sub-heading |
| `*italic-only line*` | meta line (company \| dates \| location) |

`weasyprint` is imported lazily inside `build_resume`, not at module top level — this keeps `split_frontmatter`/`render_body_html`/`render_header_html`/`build_css` importable and unit-testable on systems without WeasyPrint's native libs (pango/harfbuzz/glib), e.g. CI. `tests/test_builder.py` only exercises these pure-logic functions for this reason; it never invokes WeasyPrint itself.

`resume/cli.py` resolves `--md`/`--out` against `Path.cwd()` — content and output are always per-project, with no fallback. `--css`/`--config` prefer a same-named file in `Path.cwd()`, falling back to the bundled defaults at `resume/data/style.css` / `resume/data/config.yaml` (shipped inside the package, read via `importlib.resources`) when the current directory has none. This is what lets `resume` run from a directory containing nothing but a `resume.md` — e.g. after `uv tool install .`. `resume/data/` is the single source of truth for the default style/config; there is no root-level copy to keep in sync.
