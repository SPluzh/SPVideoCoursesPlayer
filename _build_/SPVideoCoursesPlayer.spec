# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[
        ('../resources/bin/ffprobe.exe', 'resources/bin'),
        ('../resources/bin/ffmpeg.exe', 'resources/bin'),
        ('../resources/bin/libmpv-2.dll', 'resources/bin'),
        ('../resources/bin/libmpv.version', 'resources/bin'),
    ],
    datas=[
        ('../resources/styles/dark.qss', 'resources/styles'),
        # --- Translations (editable after build) ---
        ('../resources/translations/ru.json', 'resources/translations'),
        ('../resources/translations/en.json', 'resources/translations'),
        # --- icons ---
        ('../resources/icons/*.png', 'resources/icons'),
        ('../resources/icons/*.ico', 'resources/icons'),
    ],
    hiddenimports=[
        'mutagen.mp3',
        'mutagen.mp4',
        'mutagen.flac',
        'mutagen.oggvorbis',
        'mutagen.wave',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SP Video Courses Player',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='../resources/icons/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SP Video Courses Player',
)
