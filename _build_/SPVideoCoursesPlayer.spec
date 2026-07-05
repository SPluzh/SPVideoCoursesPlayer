# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../src/main.py'],
    pathex=['../src'],
    binaries=[
        ('../src/resources/bin/ffprobe.exe', 'resources/bin'),
        ('../src/resources/bin/ffmpeg.exe', 'resources/bin'),
        ('../src/resources/bin/libmpv-2.dll', 'resources/bin'),
        ('../src/resources/bin/libmpv.version', 'resources/bin'),
    ],
    datas=[
        ('../src/resources/styles/dark.qss', 'resources/styles'),
        # --- Translations (editable after build) ---
        ('../src/resources/translations/ru.json', 'resources/translations'),
        ('../src/resources/translations/en.json', 'resources/translations'),
        # --- icons ---
        ('../src/resources/icons/*.png', 'resources/icons'),
        ('../src/resources/icons/*.ico', 'resources/icons'),
        ('../src/resources/version.txt', 'resources'),
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
    excludes=[
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtBluetooth',
        'PyQt6.QtDesigner',
        'PyQt6.QtLocation',
        'PyQt6.QtNfc',
        'PyQt6.QtPositioning',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtQuick3D',
        'PyQt6.QtQuickWidgets',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSql',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtTest',
        'PyQt6.QtTextToSpeech',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebSockets',
        'PyQt6.QtXml',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'tkinter',
        'numpy',
        'scipy',
        'pandas',
        'matplotlib',
        'cv2',
    ],
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
    strip=True,
    upx=True,
    console=False,
    icon='../src/resources/icons/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='SP Video Courses Player',
)
