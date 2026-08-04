# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\Antigravity\\AO Labs\\sonic_rip_app\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('ui', 'ui'), ('bin', 'bin')],
    hiddenimports=['webview', 'flask', 'jinja2', 'werkzeug', 'markupsafe', 'itsdangerous', 'blinker', 'click', 'mutagen', 'requests'],
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
    [],
    exclude_binaries=True,
    name='Audio_Extractor_CD_AO_Labs',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Audio_Extractor_CD_AO_Labs',
)
