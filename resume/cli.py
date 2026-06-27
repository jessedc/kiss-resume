"""Command-line entry point for the resume builder.

Run with no flags from a directory containing ``resume.md``, ``style.css``,
and ``config.yaml`` to build ``resume.pdf``.
"""

from __future__ import annotations

import argparse
import importlib.resources
import sys
from pathlib import Path

from resume.builder import build_resume


def _resolve_default(cwd_path: Path, bundled_name: str) -> Path:
    """Prefer a same-named file in the current directory; else the tool's bundled default."""
    if cwd_path.exists():
        return cwd_path
    return Path(str(importlib.resources.files("resume") / "data" / bundled_name))


def main(argv: list[str] | None = None) -> int:
    # --md and --out resolve against the current working directory, since resume
    # content and output are per-project. --css/--config fall back to the bundled
    # defaults in resume/data/ when the current directory has no copy of its own.
    cwd = Path.cwd()
    ap = argparse.ArgumentParser(
        prog="resume",
        description="Build a PDF resume from Markdown.",
    )
    ap.add_argument("--md", default=str(cwd / "resume.md"), help="input Markdown file")
    ap.add_argument(
        "--css",
        default=str(_resolve_default(cwd / "style.css", "style.css")),
        help="stylesheet (default: ./style.css, falling back to the built-in default)",
    )
    ap.add_argument(
        "--config",
        default=str(_resolve_default(cwd / "config.yaml", "config.yaml")),
        help="config YAML (default: ./config.yaml, falling back to the built-in default)",
    )
    ap.add_argument("--out", default=str(cwd / "resume.pdf"), help="output PDF path")
    args = ap.parse_args(argv)

    build_resume(
        md_path=Path(args.md),
        css_path=Path(args.css),
        config_path=Path(args.config),
        out_path=Path(args.out),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
