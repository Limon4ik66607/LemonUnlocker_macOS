# -*- mode: python ; coding: utf-8 -*-
# LemonUnlocker macOS Build Spec

block_cipher = None

a = Analysis(
    ['LemonUnlocker_v2.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),
        ('dlc_database.py', '.'),
        ('dlc_sizes.json', '.'),
        ('config.json', '.'),
        ('unlocker_mac', 'unlocker_mac'),
        ('7z', '7z'),  # Bundled 7za binary for macOS
    ],
    hiddenimports=['PyQt6', 'requests'],
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
    name='LemonUnlocker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='universal2',
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LemonUnlocker',
)

app = BUNDLE(
    coll,
    name='LemonUnlocker.app',
    icon='icon.icns',
    bundle_identifier='com.lemon4elo.lemonunlocker',
    info_plist={
        'CFBundleShortVersionString': '1.1.2',
        'CFBundleName': 'Lemon Unlocker',
        'CFBundleDisplayName': 'Lemon Unlocker',
        'NSHighResolutionCapable': True,
    },
)
