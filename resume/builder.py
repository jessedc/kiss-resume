"""Markdown -> PDF resume builder.

Pipeline:  Markdown (+ YAML frontmatter)  ->  HTML  ->  PDF (WeasyPrint)

  * Content      : resume.md   (frontmatter for name/contact, body in Markdown)
  * Presentation : style.css + config.yaml
  * Output       : a tagged PDF (PDF/UA-1) carrying a structure tree —
                   paragraph/heading/list semantics and an explicit
                   reading order.

Heading conventions in the Markdown:
    #   -> H1  section header   (Summary, Experience, ...)
    ##  -> H2  role / entry      (Senior Engineering Manager, ...)
    ### -> H3  sub-heading       (Product Achievements, ...)
    *italic line*  -> meta line  (Company | dates | location)
    <!-- break --> -> forced page break  (also: <!-- pagebreak -->, <!-- newpage -->)
"""

from __future__ import annotations

import html
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import markdown
import yaml

if TYPE_CHECKING:
    from weasyprint import HTML  # noqa: F401

# --- frontmatter -----------------------------------------------------------

PAGEBREAK_RE = re.compile(r"<!--\s*(?:break|pagebreak|newpage)\s*-->", re.I)
# Allow tags inside the <em> so an italic-only line that contains a link
# (e.g. "*[site](url) | 2023 | NYC*") is still promoted to a meta line.
META_RE = re.compile(r"<p>\s*<em>(.*?)</em>\s*</p>", re.S)
WRAPPING_P_RE = re.compile(r"^<p>(.*)</p>\s*$", re.S)

# Fallback @page values used only when config.yaml omits `page:`. The primary
# source of truth for defaults is resume/data/config.yaml; these exist so the
# no-config path (e.g. `build_css({}, "")` in tests) still produces valid CSS.
DEFAULT_PAGE_SIZE = "612pt 792pt"  # US Letter
DEFAULT_PAGE_MARGIN = "34pt 52.9pt 36pt 50.4pt"  # top right bottom left

# Must match the body font fallback in style.css: the date footer lives in a
# @page margin box, where WeasyPrint resolves neither var() nor inheritance
# from body, so the font-family has to be injected as a literal value.
DEFAULT_FONT_FAMILY = (
    '"Nimbus Sans", "Helvetica Neue", Helvetica, "Liberation Sans", Arial, sans-serif'
)
DATE_FONT_SIZE = "7.5pt"
DATE_COLOR = "#b3b3b3"

# Homebrew installs WeasyPrint's native deps to one of these; neither is on
# dlopen's default search path on macOS.
_HOMEBREW_LIB_DIRS = ("/opt/homebrew/lib", "/usr/local/lib")


def _ensure_dyld_lib_path() -> None:
    """Prepend Homebrew's lib dir to DYLD_LIBRARY_PATH so cffi.dlopen finds Pango/glib.

    Set in-process before the lazy weasyprint import. No-op off-macOS; respects an existing value. Requires a non-SIP-protected interpreter (uv's default).
    """
    if sys.platform != "darwin":
        return
    dirs = [p for p in _HOMEBREW_LIB_DIRS if Path(p).is_dir()]
    if not dirs:
        return
    existing = [p for p in os.environ.get("DYLD_LIBRARY_PATH", "").split(":") if p]
    for p in dirs:
        if p not in existing:
            existing.append(p)
    os.environ["DYLD_LIBRARY_PATH"] = ":".join(existing)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (metadata_dict, body) splitting a leading --- YAML block."""
    if text.lstrip().startswith("---"):
        parts = re.split(r"(?m)^---[ \t]*$", text, maxsplit=2)
        # parts[0] is '' (before first ---), parts[1] is YAML, parts[2] is body
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2]
    return {}, text


# --- markdown -> html ------------------------------------------------------


def render_body_html(body_md: str) -> str:
    # Replace page-break markers with a block-level div BEFORE conversion.
    body_md = PAGEBREAK_RE.sub('\n\n<div class="pagebreak"></div>\n\n', body_md)

    html_body = markdown.markdown(
        body_md,
        extensions=["extra", "sane_lists"],
        output_format="html5",  # pyright: ignore[reportArgumentType] — valid at runtime; stub only lists xhtml/html
    )

    # A paragraph that is *only* an italic line becomes a meta line.
    html_body = META_RE.sub(r'<p class="meta">\1</p>', html_body)
    return html_body


# --- header (name + contact) ----------------------------------------------


def render_header_html(meta: dict[str, Any]) -> str:
    out: list[str] = []
    name = meta.get("name")
    if name:
        out.append(f'<p class="name">{html.escape(str(name))}</p>')
    contact = meta.get("contact") or []
    if isinstance(contact, str):
        contact = [contact]
    for line in contact:
        out.append(f'<p class="contact">{_render_inline_markdown(str(line))}</p>')
    return "\n".join(out)


def _render_inline_markdown(text: str) -> str:
    """Render one line of Markdown — e.g. a contact line — so [text](url) links
    work there too, without the enclosing <p> that markdown.markdown() adds.

    Deliberately passes no `extensions=` (unlike render_body_html, which uses
    ["extra", "sane_lists"]): a contact line is a single string, so block-level
    extras like fenced code, tables, or footnotes don't apply, and core
    Markdown is enough for inline links/emphasis."""
    rendered = markdown.markdown(text)
    match = WRAPPING_P_RE.match(rendered)
    return match.group(1) if match else rendered


# --- css assembly ----------------------------------------------------------


def build_css(config: dict[str, Any], style_css: str, date_text: str | None = None) -> str:
    page = config.get("page", {}) or {}
    if isinstance(page, dict):
        size = page.get("size", DEFAULT_PAGE_SIZE)
        margin = page.get("margin", DEFAULT_PAGE_MARGIN)
    else:
        size = DEFAULT_PAGE_SIZE
        margin = DEFAULT_PAGE_MARGIN

    style_vars = config.get("style", {}) or {}

    if date_text is None:
        date_box = ""
    else:
        font_family = style_vars.get("--font-family", DEFAULT_FONT_FAMILY)
        escaped = date_text.replace("\\", "\\\\").replace('"', '\\"')
        date_box = (
            " @bottom-right {"
            f' content: "{escaped}";'
            f" font-family: {font_family};"
            f" font-size: {DATE_FONT_SIZE};"
            f" color: {DATE_COLOR};"
            " }"
        )
    page_css = f"@page {{ size: {size}; margin: {margin};{date_box} }}"

    root_css = ":root {\n" + "".join(f"  {k}: {v};\n" for k, v in style_vars.items()) + "}"

    return f"{page_css}\n{root_css}\n{style_css}"


# --- main ------------------------------------------------------------------


class BuildResult(NamedTuple):
    """Outcome of a build run; returned by build_resume for the caller to report."""

    out_path: Path


def format_date(d: date) -> str:
    """Format a date for the footer, e.g. 'July 1, 2026' (no zero-padded day)."""
    return f"{d:%B} {d.day}, {d.year}"


def build_resume(
    *,
    md_path: Path,
    css_path: Path,
    config_path: Path,
    out_path: Path,
    include_date: bool = True,
) -> BuildResult:
    """Run the full pipeline: read inputs, render HTML, write a tagged PDF.

    By default the build date is rendered in the bottom-right page margin
    (a @page margin box, so it's tagged as an artifact, not content);
    pass include_date=False to omit it.

    Returns a BuildResult describing what was written; printing/CLI feedback
    is left to the caller so this function stays reusable from non-CLI
    contexts (watch mode, library use, tests)."""
    md_text = md_path.read_text(encoding="utf-8")
    style_css = css_path.read_text(encoding="utf-8")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    meta, body_md = split_frontmatter(md_text)

    header_html = render_header_html(meta)
    body_html = render_body_html(body_md)
    date_text = format_date(date.today()) if include_date else None
    css = build_css(config, style_css, date_text=date_text)

    document = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        f"<style>\n{css}\n</style>\n</head>\n<body>\n"
        f"{header_html}\n{body_html}\n</body>\n</html>\n"
    )

    # Imported lazily so the pure-logic helpers above stay importable on systems
    # where WeasyPrint's native libs (pango/harfbuzz/glib) aren't installed — e.g. CI.
    _ensure_dyld_lib_path()  # macOS: let dlopen find Homebrew's Pango dylibs
    from weasyprint import HTML

    HTML(string=document, base_url=str(md_path.parent)).write_pdf(
        str(out_path),
        pdf_variant="pdf/ua-1",
    )
    return BuildResult(out_path=out_path)
