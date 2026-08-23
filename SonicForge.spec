# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['music_polisher_gui.py'],
    pathex=[],
    binaries=[('C:\\ffmpeg\\bin\\ffmpeg.exe', 'ffmpeg'), ('C:\\ffmpeg\\bin\\ffprobe.exe', 'ffmpeg')],
    datas=[
        ('Normalize-Music.py', '.'),
        ('assets\\sonic_forge_mark.ico', 'assets'),
        ('assets\\sonic_forge_mark.png', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='SonicForge',
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
    icon=['assets\\sonic_forge_mark.ico'],
)
