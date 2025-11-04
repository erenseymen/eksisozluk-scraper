# PowerShell build script for eksisozluk-scraper
# Requires: Python 3.8+, pip, pyinstaller

Write-Host "Building Windows executable for eksisozluk-scraper..." -ForegroundColor Cyan

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if pip is available
try {
    $pipVersion = pip --version 2>&1
    Write-Host "Found pip: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: pip is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Install/upgrade build dependencies
Write-Host "`nInstalling build dependencies..." -ForegroundColor Yellow
pip install --upgrade pip setuptools wheel
pip install pyinstaller

# Install project dependencies
Write-Host "`nInstalling project dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Clean previous builds
Write-Host "`nCleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "eksisozluk-scraper.exe") { Remove-Item -Force "eksisozluk-scraper.exe" }

# Build executable
Write-Host "`nBuilding executable..." -ForegroundColor Yellow
pyinstaller --clean eksisozluk_scraper.spec

# Check if build succeeded
if (Test-Path "dist\eksisozluk-scraper.exe") {
    Write-Host "`nBuild successful!" -ForegroundColor Green
    Write-Host "Executable location: dist\eksisozluk-scraper.exe" -ForegroundColor Green
    Write-Host "`nYou can now distribute the executable from the dist folder." -ForegroundColor Cyan
} else {
    Write-Host "`nBuild failed! Check the error messages above." -ForegroundColor Red
    exit 1
}

