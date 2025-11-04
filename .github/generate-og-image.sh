#!/bin/bash
# Script to convert SVG to PNG for GitHub social preview
# Requires: inkscape or rsvg-convert or imagemagick

SVG_FILE=".github/og-image.svg"
PNG_FILE=".github/og-image.png"

# Try different tools
if command -v inkscape &> /dev/null; then
    echo "Converting with Inkscape..."
    inkscape --export-type=png --export-filename="$PNG_FILE" --export-width=1200 --export-height=630 "$SVG_FILE"
elif command -v rsvg-convert &> /dev/null; then
    echo "Converting with rsvg-convert..."
    rsvg-convert -w 1200 -h 630 "$SVG_FILE" > "$PNG_FILE"
elif command -v convert &> /dev/null; then
    echo "Converting with ImageMagick..."
    convert -background none -resize 1200x630 "$SVG_FILE" "$PNG_FILE"
else
    echo "Error: No suitable conversion tool found."
    echo "Please install one of: inkscape, librsvg (rsvg-convert), or imagemagick"
    echo ""
    echo "Or use an online converter:"
    echo "1. Open .github/og-image.svg"
    echo "2. Convert to PNG (1200x630px) at https://convertio.co/svg-png/ or similar"
    echo "3. Save as .github/og-image.png"
    exit 1
fi

if [ -f "$PNG_FILE" ]; then
    echo "✓ Successfully created $PNG_FILE"
    echo ""
    echo "Next steps:"
    echo "1. Go to: https://github.com/erenseymen/eksisozluk-scraper/settings"
    echo "2. Scroll to 'Social preview' section"
    echo "3. Upload .github/og-image.png"
else
    echo "Error: PNG file was not created"
    exit 1
fi
