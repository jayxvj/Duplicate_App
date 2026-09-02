# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Datas to bundle into the standalone executable
datas = [
    ('web', 'web'),
    ('config', 'config'),
    ('app/config', 'app/config'),
]

hiddenimports = [
    'app',
    'app.web_server',
    'app.core',
    'app.core.types',
    'app.database',
    'app.database.db',
    'app.database.repository',
    'app.scanner',
    'app.scanner.directory_scanner',
    'app.duplicate',
    'app.duplicate.candidate_matcher',
    'app.duplicate.duplicate_detector',
    'app.categorization',
    'app.categorization.category_manager',
    'app.categorization.rule_engine',
    'app.removal',
    'app.removal.removal_manager',
    'app.removal.quarantine',
    'app.removal.safety_validator',
    'app.reporting',
    'app.reporting.report_generator',
    'app.logging',
    'app.logging.audit_logger',
    'yaml',
    'rich',
    'sqlite3',
]

excludes = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'tkinter',
    'ttkbootstrap',
    'pytest',
    'unittest',
]

a = Analysis(
    ['run_web.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='iadcs-web.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
