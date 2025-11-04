# -*- mode: python ; coding: utf-8 -*-

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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='eksisozluk-scraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

