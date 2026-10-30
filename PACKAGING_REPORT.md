# DataClean 1.0.0 — Windows packaging report

Validation date: **2026-10-30**. The portable release is prepared locally; it has not been uploaded to GitHub.

## Build and artifacts

| Item | Actual result |
| --- | --- |
| Build/test OS | Windows 11 x64, build 10.0.26200 |
| Python | CPython 3.13.5 x64 |
| PyInstaller | 6.22.3 |
| Qt / PySide6-Essentials / Shiboken | 6.12.0 |
| Layout | onedir, AMD64, Windows GUI subsystem 2; console disabled; UPX disabled |
| Application version | File/Product version 1.0.0; Stepan Pozdnyakov |
| EXE | `dist/DataClean/DataClean.exe` |
| EXE size | **9,114,838 bytes** |
| Archive | `release/DataClean-v1.0.0-win64.zip` |
| ZIP size | **58,023,955 bytes (55.34 MiB)** |
| Files in application folder / ZIP | **1,096**, including the manifest |
| Uncompressed application size | **142,429,130 bytes** |
| Digital signature | **None**; Authenticode status `NotSigned` |

EXE SHA-256:

```text
54c9b29798fc8dab5344fbf2344a3ad938c1d2496811c78c1046dbb7d6ee42a5
```

ZIP SHA-256:

```text
6263f13d9a5aa6a8cee8a19b3db57fa2ea6bd077da92a7312e3308ed35b6984c
```

The ZIP has a neighboring `.sha256` file. `release/build-info.json` records these metrics; `MANIFEST.sha256` inside the portable folder covers every other distributed file. This report stays in the source project rather than inside the ZIP whose hash it records.

## Build procedure and startup fix

The actual successful build used:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_release.ps1
```

This changes policy for that child process only. No saved Windows execution policy or security settings were changed. The normal invocation is `./build_release.ps1` where local scripts are permitted. Install `requirements-build-lock.txt` into the project-local `.venv` first. The script runs checks, renders icons, invokes PyInstaller using `DataClean.spec`, collects license notices, audits the bundle and verifies the ZIP. Downloads, temporary files and build caches stay inside the project. The lockfile and recipe support repeatable builds; byte-identical output across arbitrary systems is not guaranteed.

The first package had a real startup failure: **DLL load failed while importing QtCore: The specified procedure could not be found**. PyInstaller had resolved a private, incompatible `icuuc.dll` from a Poppler installation on the inherited PATH. The build now isolates PATH to the local Python scripts directory and Windows system directories. The spec excludes private ICU/icudt, OS API-set and ucrtbase DLLs. The final extracted EXE loads the native Windows `System32/icuuc.dll` and `icu.dll`; no system DLLs or installed Python files were changed.

Only Qt Core, Gui, Widgets and Svg are bundled. Required Qt plugins are qwindows, qico, qsvg, qsvgicon and qmodernwindowsstyle. No WebEngine, QML runtime or unused Qt Addons are included. The application icon is provided as SVG, 512 px PNG and ICO with 16, 24, 32, 48, 64, 128 and 256 px images. Resource paths work from source and the frozen `_internal` layout.

## Source checks

All checks ran from `D:\DataClean` with `.venv/Scripts/python.exe` after the release build.

| Check | Actual result |
| --- | --- |
| `-m pytest -q --tb=short` | **104 passed in 6.89s**, exit 0 |
| Existing regression tests | All previous **101** retained; no failures |
| New resource tests | **3**: working-directory independence, frozen resource layout, ICO sizes |
| `-m ruff check .` | **All checks passed**, exit 0 |
| `-m ruff format --check .` | Passed, exit 0 |
| `-m compileall -q app main.py tests examples tools` | Passed, exit 0 |
| `-m pip check` | **No broken requirements found**, exit 0 |
| Existing examples | **6/6** SHA-256 values unchanged from the earlier baseline |

Tests run Qt offscreen. Native EXE verification below is separate and does not substitute a source entry point for the packaged executable. Build/test tools and evidence are not shipped with the app.

## Final EXE verification

The **final ZIP was independently extracted** inside `test-output/release/распакованный релиз bd370072/`. The EXE tested there has exactly the EXE SHA-256 above. The full external GUI run completed successfully with **16/16 checks** in `test-output/release/e2e-b4adf707/results.json`, also copied to `test-output/release/last-success.json`.

| Operation / property | Evidence and result |
| --- | --- |
| Main window and CSV import | Actual EXE opened synthetic CSV through the native import dialog; 6 rows loaded |
| Bundled runtime | Python/Qt memory mappings all under the extracted `_internal`; no `.venv` modules |
| Duplicate removal | 6 rows became 5 |
| Empty-row removal | Whitespace-only and empty rows removed; 3 rows remained |
| Trim and CSV export | Cyrillic names trimmed; `00123`, `00045`, 40-digit ID, literal `NA` and exact decimal spelling verified in output |
| Undo | Exported values restored original surrounding spaces |
| Reset | Original 6 rows restored; reset itself could be undone |
| XLSX export | Leading-zero and long identifiers read back as literal string cells |
| XLSX import | Worksheet picker selected the second sheet; its 2 rows and city values verified through CSV export |
| Merge | Two CSV inputs combined; `00010` and `00011` preserved |
| CSV formula protection | Checked export of `=1+1` rejected with a formula warning; no output file created |
| Literal XLSX formula-like text | `=1+1` stored as a string, not a formula cell |
| XLSX long-text guard | 40,000-character value rejected with the 32,767 limit; no output created |
| Complete long CSV text | Same 40,000-character value exported and read back without truncation |
| Input protection | All **6 synthetic source files** retained their original byte hashes |
| Shutdown | Normal window close, process exit **0** |

Cyrillic filenames and directories with spaces were used throughout. The child process had a deliberately nonexistent PYTHONHOME, empty PYTHONPATH, no VIRTUAL_ENV and PATH limited to Windows System32. This verifies the local embedded-runtime layout; it is **not** a substitute for a clean machine test with Python entirely absent.

The four final EXE pages were also captured using **PrintWindow**, which captures only the application window, and visually inspected: Modern Dark colors, title-bar icon, sidebar and action SVG icons, labels, page layouts and empty states rendered correctly. Local captures are `test-output/release/final-{dashboard,data-editor,merge-files,history}.png`. They contain no overlapping desktop windows. `tools/capture_release.py` repeats this check after `tools/verify_release.py`. Existing synthetic-data screenshots remain in `assets/` for README.

Earlier partial GUI attempts exposed test-helper problems involving foreground clicks, Qt checkable button Toggle and combo-box selection. They are not counted as successful runs. The helper now directs mouse messages to the owning window, verifies each page title, sets the native filename value through UI Automation, and explicitly selects the worksheet item. No application behavior was changed to accommodate the tests.

## ZIP, confidentiality and licensing

- ZIP CRC, unique member names, expected root, safe relative paths, required embedded runtime and **all manifest hashes** passed independent verification with `tools/verify_release.py`.
- The bundle audit rejects environments, Git metadata, tests/caches, CSV/XLSX user data, logs, temporary files and local `.env` configuration. Application plaintext source files and developer tooling are not included; compiled application code needed for execution is included.
- Targeted pattern scanning of shipped binary/text files and application Python sources found **0 matches** for private keys and common OpenAI/GitHub/AWS key formats. The distributed file inventory was reviewed. No user documents were used as inputs. This is a targeted check, not a guarantee against every possible secret format.
- The bundle contains the application MIT license, dependency notices, CPython license, LGPLv3/GPL texts and Qt/PySide6 upstream notices. Official Qt Base, Qt Svg and PySide6 source archive hashes were checked against upstream SHA-256 files; provenance is recorded in `packaging/licenses/UPSTREAM-SOURCES.json`.
- `THIRD_PARTY_NOTICES.md` supplies exact corresponding-source links, build references, compatible shared-library replacement instructions and permission for reverse engineering to debug library modifications. Qt/PySide6/Shiboken remain external shared libraries. No commercial Qt license is claimed. This is a technical license inventory and packaging check, not a legal opinion.

## Remaining release checks and limitations

- **Clean Windows VM without Python has not been tested.** Test on Windows 10 and Windows 11 before broad public distribution. Current native testing covered Windows 11 build 10.0.26200 only, at the current desktop scale.
- Actual Excel/LibreOffice opening, high-DPI/multi-monitor combinations and large-file stress cases were not exercised. The source tests use file-level readback to verify values and cell types.
- The EXE is unsigned. SmartScreen/unknown-publisher warnings may appear, especially after internet download; a fresh download reputation test was not performed. No protection was disabled.
- CSV has no cell types. Checked export rejects suspicious formulas without changing data, but spreadsheet programs can still reinterpret ordinary identifiers and numbers. Use XLSX text cells or explicitly import CSV columns as Text. XLSX import retains pandas inference; precision already lost cannot be recovered.
- Data and undo snapshots must fit in memory. No installer, task cancellation, persistent session or workbook-format preservation is provided.
- Before publication, perform the clean-machine smoke check and upload the ZIP and its matching `.sha256` only when the owner chooses to publish. Signing can be added separately; it requires a new checksum and verification after signing.

All project changes and new evidence stay in `D:\DataClean`. Existing user documents, Windows settings and the earlier external review ZIP were not modified. No GitHub push or release publication was performed.
