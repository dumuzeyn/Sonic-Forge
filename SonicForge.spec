# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


whisper_datas = collect_data_files('faster_whisper')
open_clip_datas = collect_data_files('open_clip')
ct2_binaries = collect_dynamic_libs('ctranslate2')
torch_binaries = collect_dynamic_libs('torch')


a = Analysis(
    ['music_polisher_gui.py'],
    pathex=[],
    binaries=[('C:\\ffmpeg\\bin\\ffmpeg.exe', 'ffmpeg'), ('C:\\ffmpeg\\bin\\ffprobe.exe', 'ffmpeg')] + ct2_binaries + torch_binaries,
    datas=[
        ('Normalize-Music.py', '.'),
        ('assets\\sonic_forge_mark.ico', 'assets'),
        ('assets\\sonic_forge_mark.png', 'assets'),
    ] + whisper_datas + open_clip_datas,
    hiddenimports=[
        'faster_whisper',
        'faster_whisper.audio',
        'faster_whisper.tokenizer',
        'faster_whisper.transcribe',
        'ctranslate2',
        'av',
        'ftfy',
        'open_clip',
        'open_clip.factory',
        'open_clip.model',
        'open_clip.tokenizer',
        'timm',
        'torch',
        'torchvision',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'IPython',
        'jedi',
        'jsonschema',
        'matplotlib',
        'nbformat',
        'pandas',
        'pytest',
        'tensorflow',
        'torchaudio',
    ],
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
