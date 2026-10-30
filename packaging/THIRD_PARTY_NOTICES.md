# DataClean 1.0.0 — third-party notices

DataClean is Copyright (c) 2026 Stepan Pozdnyakov, distributed under the MIT license in `LICENSE`.
It includes unmodified third-party components, which retain their own terms.

## Qt, PySide6 and Shiboken

**This application uses Qt and Qt for Python (PySide6 and Shiboken), version 6.12.0, under the GNU Lesser General Public License, version 3 (LGPLv3). No commercial Qt license is claimed.**

The bundled Qt modules are Core, Gui, Widgets and Svg. Shared Qt DLLs and Python extension libraries remain external to the application executable in `_internal/PySide6/` and `_internal/shiboken6/`. There is no restriction in DataClean against reverse engineering for debugging changes to these libraries, replacing them with compatible modified versions, or running the resulting application.

To use replacement libraries, keep a backup of the extracted application folder, build ABI-compatible Windows x64 libraries using the corresponding upstream source and build instructions, then replace the matching DLLs/PYD files under `_internal`. Use compatible Qt, PySide6 and Shiboken versions together. DataClean does not verify a vendor signature or hash to prevent replacement. Its distribution manifest is an integrity aid, not an execution restriction. The included Python runtime is CPython 3.13 x64; replacement extensions must remain compatible with it.

The corresponding, unmodified source and build instructions can be obtained without charge from:

- Qt Base (Core/Gui/Widgets): https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz
- Qt Svg: https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz
- PySide6 and Shiboken: https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz
- Qt build instructions: https://doc.qt.io/qt-6/build-sources.html
- Qt for Python build instructions: https://doc.qt.io/qtforpython-6/building_from_source/index.html

Archive versions, URLs and verified SHA-256 values are recorded in `LICENSES/UPSTREAM-SOURCES.json`. The LGPLv3/GPL texts and upstream copyright and third-party notices are included under `LICENSES/qt-source-notices/`. Source archives are hosted separately from the binary for practical download size; these direct links provide the corresponding source access. Qt's licensing documentation is at https://www.qt.io/development/open-source-lgpl-obligations.

## Python and processing libraries

`LICENSES/COMPONENTS.json` records the actual wheel versions and declared licenses used for this build. Copies of the distributions' license files are retained under `LICENSES/wheels/`.

- CPython 3.13.5: PSF license and historical notices in `LICENSES/PYTHON-LICENSE.txt`.
- pandas: BSD-3-Clause.
- NumPy and its bundled numerical runtime components: BSD and additional licenses/notices supplied by its wheel, including applicable runtime exceptions.
- openpyxl and et-xmlfile: MIT.
- charset-normalizer and six: MIT.
- python-dateutil: Apache-2.0 OR BSD-3-Clause.
- tzdata: Apache-2.0 distribution terms and the IANA database's public-domain notices.
- Python's OpenSSL and Expat components: their included license texts; SQLite is in the public domain. Python's license file also includes bundled-component notices. Additional notices for XZ/LZMA are included.
- Microsoft Visual C++ runtime DLLs supplied with the Python/Qt distributions remain Microsoft components. Redistribution terms: https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/. The Windows operating-system ICU and API-set libraries are not copied into this bundle.
- PyInstaller 6.22.3 bootloader: GPLv2 with PyInstaller's exception permitting distribution of the generated application under its own license. Its notice is included under `LICENSES/wheels/pyinstaller/`. Corresponding bootloader/build source: https://github.com/pyinstaller/pyinstaller/tree/v6.22.3.

Build/test tools such as pytest, Ruff, Pillow and pywinauto are not part of the application runtime. Keep all license files and notices with copies of the portable application.
