"""Integration test: text extraction order and bullet markers in the built PDF.

Unlike test_builder.py (pure logic only), this builds a real PDF, so it needs
WeasyPrint's native libs (pango/harfbuzz/glib) and is skipped where they are
unavailable — e.g. CI. It guards the fix for content-stream scrambling: bullet
markers must be normal inline flow, never absolutely positioned, because
positioned elements are painted in a later pass and stream-order extractors
(pypdf, ATS resume parsers, macOS Preview copy/paste) then read list items out
of document order.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import pytest

from resume.builder import _ensure_dyld_lib_path, build_resume

DOCS_MD = Path(__file__).resolve().parent.parent / "docs" / "resume.md"
BULLET = "●"  # default --bullet-char ●


def _weasyprint_loads() -> bool:
    _ensure_dyld_lib_path()  # macOS: same env fix build_resume applies before its lazy import
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _weasyprint_loads(), reason="WeasyPrint native libs not available"
)


@pytest.fixture(scope="module")
def extracted_text(tmp_path_factory: pytest.TempPathFactory) -> str:
    from pypdf import PdfReader

    data = importlib.resources.files("resume") / "data"
    out_pdf = tmp_path_factory.mktemp("pdf") / "out.pdf"
    build_resume(
        md_path=DOCS_MD,
        css_path=Path(str(data / "style.css")),
        config_path=Path(str(data / "config.yaml")),
        out_path=out_pdf,
        include_date=False,
    )
    reader = PdfReader(str(out_pdf))
    return "\n".join(page.extract_text() for page in reader.pages)


def test_bullets_extract_in_document_order(extracted_text: str) -> None:
    """List items must land between their own heading and the next one."""
    landmarks = [
        "Achievements",
        "Grew the team from 4 to 12",
        "Partnered with product and design",
        "Senior Software Engineer",
        "Designed and built a notifications service",
        "Example Labs",  # third role's meta line (page 2)
        "Built and maintained REST APIs",
        "EDUCATION",
    ]
    positions = [extracted_text.find(landmark) for landmark in landmarks]
    assert all(p != -1 for p in positions), f"missing landmarks: {landmarks=} {positions=}"
    assert positions == sorted(positions), (
        f"extraction order does not match document order: {list(zip(landmarks, positions, strict=True))}"
    )


def test_html_output_is_written_alongside_pdf(tmp_path: Path) -> None:
    """--html writes a .html sibling of the PDF, and the PDF still builds.

    The screen presentation lives in style.css's `@media screen` block; the
    existing extraction tests above use that same stylesheet, so they double as
    the guard that none of it leaks into the print rendering.
    """
    data = importlib.resources.files("resume") / "data"
    out_pdf = tmp_path / "resume.pdf"
    result = build_resume(
        md_path=DOCS_MD,
        css_path=Path(str(data / "style.css")),
        config_path=Path(str(data / "config.yaml")),
        out_path=out_pdf,
        include_date=False,
        write_html=True,
    )
    assert result.html_path == tmp_path / "resume.html"
    assert result.html_path is not None
    html_text = result.html_path.read_text(encoding="utf-8")
    assert "<title>Sam Rivera</title>" in html_text
    assert '<div class="sheet">' in html_text
    assert "@media screen" in html_text  # the stylesheet is inlined, not linked
    assert out_pdf.is_file()


def test_no_html_output_by_default(tmp_path: Path) -> None:
    data = importlib.resources.files("resume") / "data"
    result = build_resume(
        md_path=DOCS_MD,
        css_path=Path(str(data / "style.css")),
        config_path=Path(str(data / "config.yaml")),
        out_path=tmp_path / "resume.pdf",
        include_date=False,
    )
    assert result.html_path is None
    assert not (tmp_path / "resume.html").exists()


def test_bullet_markers_are_inline_with_item_text(extracted_text: str) -> None:
    """Each marker must extract as a prefix of its item, never as an orphan line."""
    marker_lines = [line for line in extracted_text.splitlines() if BULLET in line]
    assert len(marker_lines) == 7, f"expected 7 bullet items, got {len(marker_lines)}"
    for line in marker_lines:
        assert line.startswith(BULLET), f"marker not at start of item: {line!r}"
        assert len(line.rstrip()) > 1, f"orphaned bullet marker on its own line: {line!r}"
