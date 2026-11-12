# -*- mode: python ; coding: utf-8 -*-
# Derleme: pyinstaller ScreenPet.spec

import re

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
)

with open('screenpet/__init__.py', encoding='utf-8') as f:
    VERSION = re.search(r'__version__\s*=\s*"([^"]+)"', f.read()).group(1)
_parts = tuple(int(p) for p in (VERSION.split('.') + ['0'] * 4)[:4])

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_parts, prodvers=_parts),
    kids=[
        StringFileInfo([StringTable('041F04B0', [
            StringStruct('ProductName', 'ScreenPet'),
            StringStruct('FileDescription', 'ScreenPet - Masaüstü Hayvanı'),
            StringStruct('FileVersion', VERSION),
            StringStruct('ProductVersion', VERSION),
            StringStruct('OriginalFilename', 'ScreenPet.exe'),
            StringStruct('LegalCopyright', 'MIT License'),
        ])]),
        VarFileInfo([VarStruct('Translation', [0x041F, 1200])]),
    ],
)

# Sadece varsayılan görseller paketlenir; UserSchema klasörleri kullanıcıya aittir.
datas = [
    ('Assets/Animal/Default', 'Assets/Animal/Default'),
    ('Assets/House/Default', 'Assets/House/Default'),
    ('Assets/Ball/Default', 'Assets/Ball/Default'),
    ('Assets/Icon', 'Assets/Icon'),
    ('languages.json', '.'),
]

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ScreenPet',
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
    icon='Assets/Icon/screenpet.ico',
    version=version_info,
)
