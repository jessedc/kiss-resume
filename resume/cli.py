"""Command-line entry point for the resume builder.

Run with no flags from a directory containing ``resume.md``, ``style.css``,
and ``config.yaml`` to build ``resume.pdf``.
"""

from __future__ import annotations

import argparse
import importlib.metadata
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
    # Use None defaults so we can tell "user passed --md explicitly" (must exist)
    # from "user accepted the default" (resolved via _resolve_default, which may
    # legitimately point at a bundled file).
    ap.add_argument("--md", default=None, help="input Markdown file")
    ap.add_argument(
        "--css",
        default=None,
        help="stylesheet (default: ./style.css, falling back to the built-in default)",
    )
    ap.add_argument(
        "--config",
        default=None,
        help="config YAML (default: ./config.yaml, falling back to the built-in default)",
    )
    ap.add_argument("--out", default=None, help="output PDF path")
    ap.add_argument(
        "-V",
        "--version",
        action="version",
        version=importlib.metadata.version("resume"),
    )
    args = ap.parse_args(argv)

    md_path = Path(args.md) if args.md is not None else cwd / "resume.md"
    out_path = Path(args.out) if args.out is not None else cwd / "resume.pdf"
    css_path = (
        Path(args.css) if args.css is not None else _resolve_default(cwd / "style.css", "style.css")
    )
    config_path = (
        Path(args.config)
        if args.config is not None
        else _resolve_default(cwd / "config.yaml", "config.yaml")
    )

    # Validate only paths the user is *responsible* for: an explicitly-passed
    # flag pointing at a missing file is a user error. Omitted --css/--config
    # already fall back to a bundled default that ships with the package, so
    # they don't need an existence check here.
    if not md_path.is_file():
        ap.error(f"input Markdown not found: {md_path}")
    if args.css is not None and not css_path.is_file():
        ap.error(f"stylesheet not found: {css_path}")
    if args.config is not None and not config_path.is_file():
        ap.error(f"config not found: {config_path}")

    result = build_resume(
        md_path=md_path,
        css_path=css_path,
        config_path=config_path,
        out_path=out_path,
    )
    print(f"Wrote {result.out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
