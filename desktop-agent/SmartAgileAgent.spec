# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the SmartAgile desktop agent.

Build:  pyinstaller SmartAgileAgent.spec
Output: dist/SmartAgileAgent.exe  (one-file, Windows)

Notes:
- The bundled ``models/`` directory is added as data; ``agent/core/classifier.py``
  resolves it from ``sys._MEIPASS`` when frozen.
- scikit-learn / pywinctl pull in submodules and data PyInstaller can't always see by
  static analysis, so we collect them explicitly below.
- ``uiautomation`` (optional browser-URL capture) is intentionally NOT bundled; it is
  imported lazily at runtime only when ``SMARTAGILE_BROWSER_URL=1``.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = []
for pkg in ("sklearn", "pywinctl", "pymonctl", "pywinbox"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass
hiddenimports += [
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    "comtypes",
    "sklearn.utils._typedefs",
    "sklearn.neighbors._partition_nodes",
]

datas = [("models", "models")]
try:
    datas += collect_data_files("sklearn")
except Exception:
    pass

a = Analysis(
    ["continous_task.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "uiautomation"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SmartAgileAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
