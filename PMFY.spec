# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all essential data files (ONNX models, phonetic DBs, fonts, QSS)
datas = []
datas += collect_data_files('rapidocr_onnxruntime')
datas += collect_data_files('eng_to_ipa')
datas += collect_data_files('pypinyin')
datas += collect_data_files('qfluentwidgets')
datas.append(('config.example.json', '.'))

# Collect hidden modules
hiddenimports = [
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'comtypes',
    'comtypes.stream',
    'comtypes.client',
    'win32gui',
    'win32con',
    'win32api',
    'win32process',
    'rapidocr_onnxruntime',
    'onnxruntime',
    'qfluentwidgets',
    'edge_tts',
    'eng_to_ipa',
    'pypinyin',
]
hiddenimports += collect_submodules('qfluentwidgets')
hiddenimports += collect_submodules('rapidocr_onnxruntime')

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas', 'IPython', 'notebook', 'pytest'],
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
    name='PMFY',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PMFY',
)
