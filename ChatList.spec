# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))
from version import __version__, dist_exe_name

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[str(Path(SPECPATH))],
    binaries=[],
    datas=[("app.ico", ".")],
    hiddenimports=["version"],
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
    name=dist_exe_name(),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(Path(SPECPATH) / "app.ico"),
    version=f"version-{__version__}.txt",
)
