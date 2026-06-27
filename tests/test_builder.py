"""Tests for the resume builder's pure-logic units.

WeasyPrint is not exercised here (it needs system libs and is slow); the HTML/CSS
assembly functions are the parts worth pinning. Run via `uv run pytest`.
"""

from __future__ import annotations

from resume.builder import (
    build_css,
    render_body_html,
    render_header_html,
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


# --- body html --------------------------------------------------------------


def test_render_body_html_converts_markdown() -> None:
    html_out = render_body_html("## Role\n\n- did thing\n")
    assert "<h2>Role</h2>" in html_out
    assert "<li>did thing</li>" in html_out


def test_render_body_html_promotes_italic_only_line_to_meta() -> None:
    html_out = render_body_html("*Acme Inc | 2023 | Springfield*\n")
    assert '<p class="meta">Acme Inc | 2023 | Springfield</p>' in html_out


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
