# Building Debian Package

This guide explains how to build the Debian package for eksisozluk-scraper.

## Prerequisites

Install the required build dependencies:

```bash
sudo apt-get update
sudo apt-get install build-essential debhelper dh-python python3-all python3-setuptools
```

### Note on Python Dependencies

The package dependencies (cloudscraper, beautifulsoup4, argcomplete) will be installed via pip during package installation. If these packages are not available in Debian repositories, they will be installed from PyPI automatically by the package manager.

If you encounter dependency issues, you may need to install them manually:
```bash
sudo apt-get install python3-pip
pip3 install cloudscraper beautifulsoup4 argcomplete
```

## Building the Package

### Method 1: Using Makefile

```bash
make build-deb
```

This will create the Debian package in the parent directory.

### Method 2: Using dpkg-buildpackage directly

```bash
dpkg-buildpackage -us -uc -b
```

This builds a binary package without signing it.

### Building a Source Package

To build a source package:

```bash
make build-source
# or
dpkg-buildpackage -S -us -uc
```

## Installing the Package

After building, install the package:

```bash
sudo dpkg -i ../eksisozluk-scraper_*.deb
```

If there are missing dependencies:

```bash
sudo apt-get install -f
```

## Testing Tab Completion

After installation, restart your shell or run:

```bash
source /usr/share/bash-completion/bash_completion
```

Then test tab completion:

```bash
eksisozluk-scraper <TAB>
eksisozluk-scraper --<TAB>
```

## Cleaning Build Artifacts

```bash
make clean
```

## Package Structure

The Debian package includes:
- `eksisozluk-scraper` executable in `/usr/bin/`
- Bash completion script in `/usr/share/bash-completion/completions/`
- Python module in `/usr/lib/python3/dist-packages/`

