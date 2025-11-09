#!/usr/bin/env python3
"""Build the Windows installer (MSI) using Pynsist."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, cwd: Path) -> int:
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}", file=sys.stderr)
    return result.returncode


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist"
    cfg_path = project_root / "windows" / "installer.cfg"

    if run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir)], cwd=project_root):
        return 1

    if run([sys.executable, "-m", "pynsist", str(cfg_path)], cwd=project_root):
        return 1

    print("Pynsist build finished. MSI is available in the build/nsis/ directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

