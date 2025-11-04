# -*- mode: python ; coding: utf-8 -*-
# Alternative one-dir build spec - Sometimes less likely to trigger false positives
# Usage: pyinstaller --clean eksisozluk_scraper_onedir.spec

block_cipher = None

a = Analysis(
    ['eksisozluk_scraper.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'cloudscraper',
        'bs4',
        'beautifulsoup4',
        'argcomplete',
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'lxml',
        'soupsieve',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='eksisozluk-scraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='eksisozluk-scraper',
)

