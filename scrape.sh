#!/bin/bash
# Ekşi Sözlük Scraper wrapper script

# Virtual environment'i aktif et
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Scraper'ı çalıştır
python eksisozluk_scraper.py "$@"

