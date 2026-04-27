# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('lang', 'lang'),
        ('themes', 'themes'),
        ('firebase-config.json', '.'),
        ('settings.json', '.'),
        ('sport_presets.json', '.'),
        ('categories.json', '.'),
    ],
    hiddenimports=[
        'PySide6',
        'firebase_admin',
        'requests',
        'urllib3',
        # Explicitly force PyInstaller to pack every single flattened page:
        'GUI_windows.admin_tools',
        'GUI_windows.confirm',
        'GUI_windows.dashboard',
        'GUI_windows.leaderboard_page',
        'GUI_windows.league_page',
        'GUI_windows.login',
        'GUI_windows.race_page',
        'GUI_windows.timing_page',
        'core.config_manager',
        'core.firebase_service',
        'core.sport_logic',
        'core.translate',
    ],
    packages=['core', 'GUI_windows'],  
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Stopwatch Control',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='MyIcon.icns',  
)

app = BUNDLE(
    exe,
    name='StopwatchControl.app',
    icon='MyIcon.icns',  
    bundle_identifier='com.stopwatchcontrol.app',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
    },
)