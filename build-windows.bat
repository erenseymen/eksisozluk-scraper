@echo off
REM Windows build script for eksisozluk-scraper
REM Requires: Python 3.8+, pip, pyinstaller

echo Building Windows executable for eksisozluk-scraper...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo Error: pip is not installed or not in PATH
    exit /b 1
)

REM Install/upgrade build dependencies
echo Installing build dependencies...
pip install --upgrade pip setuptools wheel
pip install pyinstaller

REM Install project dependencies
echo Installing project dependencies...
pip install -r requirements.txt

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist eksisozluk-scraper.exe del /q eksisozluk-scraper.exe

REM Build executable
echo Building executable...
pyinstaller --clean eksisozluk_scraper.spec

REM Check if build succeeded
if exist dist\eksisozluk-scraper.exe (
    echo.
    echo Build successful!
    echo Executable location: dist\eksisozluk-scraper.exe
    echo.
    echo You can now distribute the executable from the dist folder.
) else (
    echo.
    echo Build failed! Check the error messages above.
    exit /b 1
)

