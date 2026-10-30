# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)

a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'assets' / name), 'assets') for name in ('icon.ico', 'icon.png', 'icon.svg')],
    hiddenimports=['openpyxl', 'pandas.io.excel._openpyxl'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'IPython', 'pytest', 'pytestqt', 'ruff',
        'PIL', 'pywinauto', 'comtypes', 'psutil',
        'PySide6.QtNetwork', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
        'PySide6.QtMultimedia', 'PySide6.QtPrintSupport', 'PySide6.QtSql', 'PySide6.QtTest',
        'PySide6.QtOpenGLWidgets', 'PySide6.QtPdf', 'PySide6.QtDesigner',
    ],
    noarchive=False,
)
# Keep only the plugin families used by this Widgets application. PNG support is
# built into QtGui; ICO and SVG are the only external image handlers required.
qt_modules = {'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'Qt6Svg.dll'}

def needed_binary(entry):
    destination = entry[0].replace('\\', '/')
    filename = destination.rsplit('/', 1)[-1]
    # This Qt build uses the Windows ICU API, not an unrelated private ICU build.
    # Windows supplies these OS libraries; do not redistribute PATH-discovered copies.
    if filename.lower() in {'icuuc.dll', 'icu.dll', 'ucrtbase.dll'} or filename.lower().startswith(('icudt', 'api-ms-win-')):
        return False
    if filename.startswith('Qt6') and filename.endswith('.dll'):
        return filename in qt_modules
    if '/plugins/platforms/' in destination:
        return filename == 'qwindows.dll'
    if '/plugins/imageformats/' in destination:
        return filename in {'qico.dll', 'qsvg.dll'}
    if '/plugins/' in destination:
        return '/iconengines/' in destination or '/styles/' in destination
    return True

a.binaries = [entry for entry in a.binaries if needed_binary(entry)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='DataClean',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(root / 'assets' / 'icon.ico'),
    version=str(root / 'packaging' / 'windows_version.txt'),
    contents_directory='_internal',
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DataClean')
