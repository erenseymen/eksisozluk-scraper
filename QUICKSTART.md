# Quick Start Guide

## Installation

### Option 1: Debian Package (Recommended)

```bash
# Build the package
make build-deb

# Install
sudo dpkg -i ../eksisozluk-scraper_*.deb
sudo apt install -f  # Fix any missing dependencies
```

### Option 2: Python Package (Development)

```bash
# Install package (includes dependencies)
pip3 install -e .

# Now you can use the eksisozluk-scraper command
eksisozluk-scraper "python"

# Alternatively, for development, you can run directly:
python3 eksisozluk_scraper.py "python"
```

## Usage

### Basic Usage

```bash
# Scrape all entries from a title
eksisozluk-scraper "python"

# Scrape last 7 days
eksisozluk-scraper "python" --days 7

# Save to file
eksisozluk-scraper "python" --output results.json
```

### Tab Completion

After installation, tab completion is automatically enabled in bash:

```bash
eksisozluk-scraper <TAB>              # Shows options
eksisozluk-scraper --<TAB>             # Lists all flags
eksisozluk-scraper --output <TAB>     # Completes file names
```

If tab completion doesn't work automatically:

```bash
# For bash
eval "$(register-python-argcomplete eksisozluk-scraper)"

# For zsh
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete eksisozluk-scraper)"
```

## Examples

### Time Filtering

```bash
# Last 1 day
eksisozluk-scraper "python" --days 1

# Last 2 weeks
eksisozluk-scraper "python" --weeks 2

# Last 1 month
eksisozluk-scraper "python" --months 1

# Last 1 year
eksisozluk-scraper "python" --years 1

# Entries between specific dates (inclusive)
eksisozluk-scraper "python" --start 2024.01.01 --end 2024.01.31

# Entries from a start date
eksisozluk-scraper "python" --start 2024.02.01

# Entries up to a given date
eksisozluk-scraper "python" --end 2024.02.01
```

### Limit Entries

```bash
# Maximum 100 entries
eksisozluk-scraper "python" --max-entries 100
```

### Output Formats

```bash
# JSON (default)
eksisozluk-scraper "python" --output results.json

# CSV
eksisozluk-scraper "python" --output results.csv

# Markdown
eksisozluk-scraper "python" --output results.md
```

### Advanced Options

```bash
# Custom delay between requests
eksisozluk-scraper "python" --delay 2.0

# More retries
eksisozluk-scraper "python" --max-retries 5

# Disable referenced entries (bkz)
eksisozluk-scraper "python" --no-bkz
```

### Scrape from Specific Entry

```bash
eksisozluk-scraper "https://eksisozluk.com/python--123456"
```

## Troubleshooting

### Tab Completion Not Working

1. Ensure `argcomplete` is installed:
   ```bash
   pip3 install argcomplete
   ```

2. Activate completion manually:
   ```bash
   eval "$(register-python-argcomplete eksisozluk-scraper)"
   ```

3. Add to your shell config (`~/.bashrc` or `~/.zshrc`)

### Package Installation Issues

If package installation fails with dependency errors:

```bash
sudo apt install -f
sudo apt install python3-pip
pip3 install cloudscraper beautifulsoup4 argcomplete
```

### Permission Errors

If you get permission errors, ensure the executable is in your PATH:

```bash
which eksisozluk-scraper
```

If not found, you may need to reinstall or use the full path.

