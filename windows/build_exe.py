#!/usr/bin/env python3
"""Utility to build the standalone Windows executable via PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    spec_path = project_root / "eksisozluk_scraper.spec"

    if not spec_path.exists():
        print(f"PyInstaller spec not found at {spec_path}", file=sys.stderr)
        return 1

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path),
    ]

    print("Running:", " ".join(cmd))
    process = subprocess.run(cmd, cwd=project_root)
    if process.returncode != 0:
        print("PyInstaller build failed.", file=sys.stderr)
    else:
        print("PyInstaller build finished. Check the dist/ directory.")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())

