# Social Preview Image

This directory contains the social preview image (Open Graph image) for the repository.

## Files

- `og-image.svg` - Source SVG file (editable)
- `og-image.png` - Rendered PNG file (1200x630px) ready for GitHub

## How to Set Up on GitHub

1. Go to your repository settings: https://github.com/erenseymen/eksisozluk-scraper/settings
2. Scroll down to the **"Social preview"** section
3. Click **"Upload an image"** or drag and drop
4. Upload `.github/og-image.png`
5. GitHub will automatically use this image when the repository link is shared on social media platforms

## Regenerating the PNG

If you edit the SVG file, you can regenerate the PNG using:

```bash
./.github/generate-og-image.sh
```

Or manually with ImageMagick:

```bash
convert -background none -resize 1200x630 .github/og-image.svg .github/og-image.png
```

## Image Specifications

- **Size**: 1200x630 pixels (GitHub recommended)
- **Format**: PNG (with transparency support)
- **Aspect Ratio**: ~1.91:1 (standard for Open Graph images)
