"""Tests for the CLI's argument-resolution and error paths.

WeasyPrint is not exercised here. We only cover the logic that runs *before*
`build_resume` is called: the cwd-vs-bundled default resolution and the
missing-file guards. End-to-end PDF rendering needs WeasyPrint's native libs and
is intentionally out of scope (see tests/test_builder.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from resume.cli import _resolve_default, main

# --- _resolve_default -------------------------------------------------------


def test_resolve_default_prefers_cwd_file(tmp_path: Path) -> None:
    cwd_file = tmp_path / "style.css"
    cwd_file.write_text("/* local */", encoding="utf-8")
    resolved = _resolve_default(cwd_file, "style.css")
    assert resolved == cwd_file


def test_resolve_default_falls_back_to_bundled(tmp_path: Path) -> None:
    # No cwd copy → fall back to the bundled default shipped with the package.
    resolved = _resolve_default(tmp_path / "style.css", "style.css")
    assert resolved != tmp_path / "style.css"
    # The bundled default must actually exist; this also guards against a
    # broken package build that drops resume/data/.
    assert resolved.is_file()


def test_resolve_default_bundled_config_is_valid_yaml(tmp_path: Path) -> None:
    # Sanity: the bundled config fallback is a real, readable YAML file.
    import yaml

    resolved = _resolve_default(tmp_path / "config.yaml", "config.yaml")
    assert resolved.is_file()
    assert isinstance(yaml.safe_load(resolved.read_text(encoding="utf-8")), dict)


# --- main error paths -------------------------------------------------------
# These must error out BEFORE build_resume is called, so WeasyPrint is never
# imported and the tests don't need its native libs.


def test_main_errors_on_missing_explicit_md(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "nope.md"
    with pytest.raises(SystemExit) as exc:
        main(["--md", str(missing)])
    assert exc.value.code == 2  # argparse's ap.error exit code
    err = capsys.readouterr().err
    assert "input Markdown not found" in err
    assert str(missing) in err


def test_main_errors_on_missing_explicit_css(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Provide a valid md so we get past that check, then hit the css guard.
    md = tmp_path / "resume.md"
    md.write_text("# Hi\n", encoding="utf-8")
    missing_css = tmp_path / "nope.css"
    with pytest.raises(SystemExit) as exc:
        main(["--md", str(md), "--css", str(missing_css)])
    assert exc.value.code == 2
    assert "stylesheet not found" in capsys.readouterr().err


def test_main_errors_on_missing_explicit_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    md = tmp_path / "resume.md"
    md.write_text("# Hi\n", encoding="utf-8")
    missing_cfg = tmp_path / "nope.yaml"
    with pytest.raises(SystemExit) as exc:
        main(["--md", str(md), "--config", str(missing_cfg)])
    assert exc.value.code == 2
    assert "config not found" in capsys.readouterr().err
