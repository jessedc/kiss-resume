"""Tests for the resume builder's pure-logic units.

WeasyPrint is not exercised here (it needs system libs and is slow); the HTML/CSS
assembly functions are the parts worth pinning. Run via `uv run pytest`.
"""

from __future__ import annotations

from datetime import date

from resume.builder import (
    DEFAULT_FONT_FAMILY,
    build_css,
    format_date,
    render_body_html,
    render_header_html,
    render_html_document,
    split_frontmatter,
)

# --- frontmatter -----------------------------------------------------------


def test_split_frontmatter_parses_yaml_block() -> None:
    text = "---\nname: Jane Doe\ncontact:\n  - a@b.com\n---\n# Body\n"
    meta, body = split_frontmatter(text)
    assert meta == {"name": "Jane Doe", "contact": ["a@b.com"]}
    assert body.lstrip().startswith("# Body")


def test_split_frontmatter_no_block_returns_empty_meta() -> None:
    text = "# Just a body\n"
    meta, body = split_frontmatter(text)
    assert meta == {}
    assert body == text


def test_split_frontmatter_tolerates_leading_whitespace() -> None:
    # The opening guard uses lstrip(), but re.split runs on the raw text — so a
    # leading blank line must still parse correctly.
    text = "\n---\nname: Jane Doe\n---\n# Body\n"
    meta, body = split_frontmatter(text)
    assert meta == {"name": "Jane Doe"}
    assert body.lstrip().startswith("# Body")


def test_split_frontmatter_empty_block_yields_empty_meta() -> None:
    text = "---\n---\n# Body\n"
    meta, body = split_frontmatter(text)
    assert meta == {}
    assert body.lstrip().startswith("# Body")


def test_split_frontmatter_preserves_hr_in_body_after_block() -> None:
    # maxsplit=2 means only the first two --- lines are frontmatter delimiters;
    # a thematic break later in the body must survive intact.
    text = "---\nname: Jane\n---\n# Title\n\n---\n\ntext\n"
    meta, body = split_frontmatter(text)
    assert meta == {"name": "Jane"}
    assert "\n---\n" in body  # the HR is preserved, not consumed
    assert body.lstrip().startswith("# Title")


# --- body html --------------------------------------------------------------


def test_render_body_html_converts_markdown() -> None:
    html_out = render_body_html("## Role\n\n- did thing\n")
    assert "<h2>Role</h2>" in html_out
    assert "<li>did thing</li>" in html_out


def test_render_body_html_promotes_italic_only_line_to_meta() -> None:
    html_out = render_body_html("*Acme Inc | 2023 | Springfield*\n")
    assert '<p class="meta">Acme Inc | 2023 | Springfield</p>' in html_out


def test_render_body_html_promotes_italic_line_with_link_to_meta() -> None:
    # A link inside an italic-only line inserts tags inside <em>; the meta
    # promotion must still fire so the line keeps its meta styling.
    html_out = render_body_html("*[acme.com](https://acme.com) | 2023 | NYC*\n")
    assert '<p class="meta">' in html_out
    assert '<a href="https://acme.com">acme.com</a>' in html_out
    assert 'class="meta"' in html_out


def test_render_body_html_inline_italic_stays_emphasis() -> None:
    html_out = render_body_html("some *inline* emphasis\n")
    assert "<em>inline</em>" in html_out
    assert 'class="meta"' not in html_out


def test_render_body_html_expands_pagebreak_markers() -> None:
    for marker in ("<!-- break -->", "<!-- pagebreak -->", "<!-- newpage -->"):
        html_out = render_body_html(f"before\n\n{marker}\n\nafter")
        assert '<div class="pagebreak"></div>' in html_out


def test_render_body_html_renders_markdown_link() -> None:
    html_out = render_body_html("See my [portfolio](https://example.com/jesse) for more.\n")
    assert '<a href="https://example.com/jesse">portfolio</a>' in html_out


# --- header ----------------------------------------------------------------


def test_render_header_html_renders_name_and_contact() -> None:
    html_out = render_header_html({"name": "Jane Doe", "contact": ["a@b.com", "555-1212"]})
    assert '<p class="name">Jane Doe</p>' in html_out
    assert '<p class="contact">a@b.com</p>' in html_out
    assert '<p class="contact">555-1212</p>' in html_out


def test_render_header_html_handles_string_contact() -> None:
    html_out = render_header_html({"contact": "one line"})
    assert '<p class="contact">one line</p>' in html_out


def test_render_header_html_escapes_name() -> None:
    html_out = render_header_html({"name": "<b>Jane</b>"})
    assert "&lt;b&gt;Jane&lt;/b&gt;" in html_out
    assert "<b>Jane</b>" not in html_out


def test_render_header_html_empty_meta() -> None:
    assert render_header_html({}) == ""


def test_render_header_html_renders_markdown_link_in_contact() -> None:
    html_out = render_header_html(
        {
            "contact": [
                "[linkedin.com/in/samrivera](https://linkedin.com/in/samrivera)"
                " | [github.com/samrivera](https://github.com/samrivera)"
            ]
        }
    )
    assert '<a href="https://linkedin.com/in/samrivera">linkedin.com/in/samrivera</a>' in html_out
    assert '<a href="https://github.com/samrivera">github.com/samrivera</a>' in html_out
    # the separator between the two links is preserved, not swallowed
    assert "</a> | <a" in html_out


# --- css -------------------------------------------------------------------


def test_build_css_emits_page_rule_root_vars_and_style() -> None:
    css = build_css(
        {
            "page": {"size": "595pt 842pt", "margin": "1pt 2pt 3pt 4pt"},
            "style": {"--font-family": "sans"},
        },
        "/* base */",
    )
    assert "@page { size: 595pt 842pt; margin: 1pt 2pt 3pt 4pt; }" in css
    assert "--font-family: sans;" in css
    assert "/* base */" in css


def test_build_css_uses_defaults_when_page_missing() -> None:
    css = build_css({}, "")
    assert "@page { size: 612pt 792pt;" in css
    assert "margin: 34pt 52.9pt 36pt 50.4pt;" in css


def test_build_css_falls_back_to_defaults_when_page_not_a_dict() -> None:
    # A malformed `page:` (string/list instead of mapping) shouldn't crash.
    css = build_css({"page": "oops"}, "")
    assert "@page { size: 612pt 792pt;" in css
    assert "margin: 34pt 52.9pt 36pt 50.4pt;" in css


# --- date footer -------------------------------------------------------------


def test_build_css_without_date_has_no_margin_box() -> None:
    assert "@bottom-right" not in build_css({}, "")


def test_build_css_date_box_uses_configured_font() -> None:
    css = build_css({"style": {"--font-family": "Georgia, serif"}}, "", date_text="July 1, 2026")
    assert '@bottom-right { content: "July 1, 2026"; font-family: Georgia, serif;' in css


def test_build_css_date_box_falls_back_to_default_font() -> None:
    css = build_css({}, "", date_text="July 1, 2026")
    assert f"font-family: {DEFAULT_FONT_FAMILY};" in css


def test_build_css_date_box_stays_inside_page_rule() -> None:
    # The margin box must nest inside @page — a sibling rule would be ignored.
    css = build_css({}, "", date_text="July 1, 2026")
    page_rule = css.splitlines()[0]
    assert page_rule.startswith("@page {")
    assert "@bottom-right {" in page_rule
    assert page_rule.rstrip().endswith("} }")


def test_build_css_escapes_quotes_in_date_text() -> None:
    css = build_css({}, "", date_text='1 "July" 2026')
    assert 'content: "1 \\"July\\" 2026";' in css


def test_format_date_no_zero_padding() -> None:
    assert format_date(date(2026, 7, 1)) == "July 1, 2026"


# --- html document (the optional --html output) ------------------------------


def _doc(**kwargs: str | None) -> str:
    args: dict[str, str | None] = {
        "header_html": '<p class="name">Jane</p>',
        "body_html": "<h1>Summary</h1>",
        "css": "/* css */",
        "title": "Jane Doe",
    }
    args.update(kwargs)
    return render_html_document(**args)  # type: ignore[arg-type]


def test_render_html_document_wraps_content_in_sheet() -> None:
    out = _doc()
    assert '<div class="sheet">' in out
    assert '<p class="name">Jane</p>' in out
    assert "<h1>Summary</h1>" in out
    assert "/* css */" in out


def test_render_html_document_has_viewport_meta() -> None:
    # Without this the mobile layout is rendered at desktop width and scaled down.
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in _doc()


def test_render_html_document_escapes_title() -> None:
    out = _doc(title="<script>x</script>")
    assert "<title>&lt;script&gt;x&lt;/script&gt;</title>" in out


def test_render_html_document_includes_theme_switch() -> None:
    out = _doc()
    assert 'data-theme-choice="system"' in out
    assert 'data-theme-choice="light"' in out
    assert 'data-theme-choice="dark"' in out


def test_render_html_document_theme_defaults_to_system() -> None:
    # 'system' is represented by the absence of data-theme on <html>, so the CSS
    # falls through to prefers-color-scheme.
    out = _doc()
    assert '<html lang="en">' in out
    assert "data-theme=" not in out.split("<body>")[0].replace("data-theme-choice", "")
    assert 'data-theme-choice="system" aria-pressed="true"' in out


def test_render_html_document_renders_date_as_element() -> None:
    # The PDF's @page margin box doesn't render on screen, so the HTML needs a
    # real element for the date.
    out = _doc(date_text="July 1, 2026")
    assert '<p class="sheet-date">July 1, 2026</p>' in out


def test_render_html_document_omits_date_element_when_absent() -> None:
    assert "sheet-date" not in _doc(date_text=None)


def test_render_html_document_escapes_date_text() -> None:
    assert "&lt;b&gt;" in _doc(date_text="<b>July</b>")
