# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

project_root = Path(__file__).parent.resolve()

datas = []
# Bundled data files required by optional runtime dependencies.
datas += collect_data_files('trafilatura', include_py_files=False)
datas += collect_data_files('rich', include_py_files=False)
datas += collect_data_files('youtube_transcript_api', include_py_files=False)

hiddenimports = [
    'argcomplete',
    'beautifulsoup4',
    'bs4',
    'charset_normalizer',
    'cloudscraper',
    'courlan',
    'lxml',
    'markdown_it',
    'requests',
    'soupsieve',
    'trafilatura',
    'urllib3',
    'youtube_transcript_api',
] + collect_submodules('trafilatura') + collect_submodules('rich')

a = Analysis(
    ['eksisozluk_scraper.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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

