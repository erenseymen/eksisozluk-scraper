# Windows Builds

This repository ships scripts for producing Windows-friendly artifacts of the CLI:

- A standalone `eksisozluk-scraper.exe` console application built with PyInstaller.
- An MSI installer built with Pynsist that deploys the command to PATH, mirroring the Linux package experience.

> **Note:** Build the artifacts on Windows for best results. Cross-compiling from Linux is not supported by the upstream tooling.

## Prerequisites

- Python 3.11 (the bundled runtime in the MSI matches this version).
- A virtual environment with the project dependencies:
  ```bash
  python -m venv .venv
  .\.venv\Scripts\activate
  pip install -r requirements.txt
  ```
- Build tooling:
  ```bash
  pip install build pynsist pyinstaller
  ```

## Standalone Executable (`eksisozluk-scraper.exe`)

1. Activate your virtual environment.
2. Run the helper:
   ```bash
   python windows/build_exe.py
   ```
3. The executable is written to `dist/eksisozluk-scraper.exe`. Distribute that file as-is.

## MSI Installer

1. Activate your virtual environment.
2. Build the MSI:
   ```bash
   python windows/build_installer.py
   ```
   The script first produces a wheel in `dist/`, then invokes Pynsist with `windows/installer.cfg`.
3. Find the resulting installer in `build/nsis/`. Running it on Windows sets up the `eksisozluk-scraper` command and adds it to PATH.

## Troubleshooting

- If optional integrations (Gemini output, Trafilatura parsing, etc.) are required, ensure the corresponding dependencies remain listed in `requirements.txt`. The PyInstaller spec and MSI configuration pull from this list.
- To clean previous builds, delete the `build/` and `dist/` directories before rebuilding.

