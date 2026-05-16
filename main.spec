# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_submodules


python_root = sys.base_prefix
python_dlls = os.path.join(python_root, 'DLLs')
python_tcl = os.path.join(python_root, 'tcl')
system32 = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')


def keep_runtime_module(name):
    return ".tests" not in name and "._tests" not in name and "._tools" not in name


hiddenimports = (
    [
        'tkinter',
        'tkinter.ttk',
        'tkinter.font',
        'tkinter.filedialog',
        'tkinter.constants',
        '_tkinter',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'winrt.windows.globalization',
        'winrt.windows.graphics.imaging',
        'winrt.windows.media.ocr',
        'winrt.windows.storage.streams',
    ]
    + collect_submodules('winrt', filter=keep_runtime_module)
    +
    collect_submodules('selenium', filter=keep_runtime_module)
    + collect_submodules('selenium.webdriver.common.devtools', filter=keep_runtime_module)
    + collect_submodules('selenium.webdriver.common.bidi', filter=keep_runtime_module)
    + collect_submodules('selenium.webdriver.remote', filter=keep_runtime_module)
    + collect_submodules('trio', filter=keep_runtime_module)
    + collect_submodules('trio_websocket', filter=keep_runtime_module)
    + collect_submodules('wsproto', filter=keep_runtime_module)
    + collect_submodules('websocket', filter=keep_runtime_module)
    + collect_submodules('urllib3', filter=keep_runtime_module)
    + collect_submodules('certifi', filter=keep_runtime_module)
    + collect_submodules('outcome', filter=keep_runtime_module)
    + collect_submodules('sniffio', filter=keep_runtime_module)
    + collect_submodules('sortedcontainers', filter=keep_runtime_module)
    + collect_submodules('attr', filter=keep_runtime_module)
)


def collect_existing_binaries(names, search_roots):
    binaries = []
    seen = set()

    for name in names:
        for root in search_roots:
            path = os.path.join(root, name)
            key = os.path.normcase(os.path.abspath(path))
            if key in seen or not os.path.exists(path):
                continue

            binaries.append((path, '.'))
            seen.add(key)
            break

    return binaries


runtime_binaries = collect_existing_binaries(
    [
        f'python{sys.version_info.major}{sys.version_info.minor}.dll',
        'vcruntime140.dll',
        'vcruntime140_1.dll',
        'msvcp140.dll',
        'concrt140.dll',
    ],
    [python_root, python_dlls, system32],
)


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=runtime_binaries + [
        (os.path.join(python_dlls, '_tkinter.pyd'), '.'),
        (os.path.join(python_dlls, 'tcl86t.dll'), '.'),
        (os.path.join(python_dlls, 'tk86t.dll'), '.'),
    ],
    datas=[
        ('app_icon.ico', '.'),
        ('Join Rain Event.png', '.'),
        ('Rain Joined.png', '.'),
        ('100 % off .png', '.'),
        ('Rain amount.png', '.'),
        ('Rain results.png', '.'),
        ('rain_alert.wav', '.'),
        (os.path.join(python_root, 'Lib', 'tkinter'), 'tkinter'),
        (os.path.join(python_tcl, 'tcl8.6'), '_tcl_data'),
        (os.path.join(python_tcl, 'tk8.6'), '_tk_data'),
        (os.path.join(python_tcl, 'tcl8'), os.path.join('_tcl_data', 'tcl8')),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook_tkinter.py'],
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
    name='RainBarrel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='app_icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
