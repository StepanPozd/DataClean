# DataClean 1.0.1 — Windows packaging report

Validation date: **2026-10-30**. Prepared locally from `main` at `37670b6`, including the Qt worker-lifetime changes from `bf3ca37`, current test fixes and CI diagnostics, plus this release's version/documentation updates. No push or publication was performed.

## Artifact and build environment

| Item | Actual result |
| --- | --- |
| OS | Windows 11 x64, 10.0.26200 |
| Embedded/build Python | **3.13.5 x64** |
| PyInstaller | **6.22.3** |
| PySide6-Essentials / shiboken6 / Qt | **6.12.0** |
| pandas / NumPy / openpyxl | 3.1.0 / 2.5.4 / 3.1.5 |
| Layout | Windows x64 onedir, GUI subsystem 2; console disabled, UPX disabled |
| Version | Application/sidebar 1.0.1; EXE File/Product version 1.0.1, fixed version 1.0.1.0 |
| EXE | `dist/DataClean/DataClean.exe` |
| EXE size | **9,115,261 bytes** |
| ZIP | `release/DataClean-v1.0.1-win64.zip` |
| ZIP size | **58,023,831 bytes (55.34 MiB)** |
| Uncompressed distribution | **142,431,226 bytes** |
| File count | **1,096**, including MANIFEST.sha256 |
| Digital signature | **None**; Authenticode status NotSigned |

ZIP SHA-256:

```text
b67e1d19c9496b3277f3e4237e684803e8af9d2f9e86c978811d9e515f5f528a
```

EXE SHA-256:

```text
97575d20824baab944054fa7ff8576782e62211e114fb17bb52916c278b3b959
```

`release/DataClean-v1.0.1-win64.zip.sha256` and `release/build-info.json` record the archive checksum and build metrics. `MANIFEST.sha256` inside the portable folder covers every other distributed file. This report stays in the source project rather than in the archive whose hash it records.

## Build procedure

The existing process was run with all checks enabled:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_release.ps1
```

Bypass applies only to that child process; no saved Windows execution policy was changed. The project-local `.venv` and existing `requirements-build-lock.txt` were used. Dependency versions were not upgraded or downgraded. The recipe is reproducible from the recorded environment; byte-identical binaries across arbitrary systems are not promised.

The script rendered the existing SVG icon, built `DataClean.spec` with PyInstaller `--clean`, assembled the notices, checked the distribution and created the ZIP. Build PATH remained isolated to local Python scripts and Windows directories to exclude incompatible private ICU DLLs. Final runtime mappings show native Windows System32 ICU and Python/Qt DLLs under the extracted application's `_internal`, with no `.venv` modules.

Only Qt Core, Gui, Widgets and Svg plus required Windows/image/icon/style plugins are included. The window icon and Modern Dark design are unchanged; source screenshots were regenerated with synthetic examples to display the current version. Version metadata was updated in the Python package, QApplication, sidebar, Windows resources, guide, notices and archive tooling.

## Source verification

| Check | Actual result |
| --- | --- |
| Build-environment pytest, Python 3.13.5 | **115 passed in 9.31s**, exit 0 |
| Fresh CI-matching environment, Python 3.11.9 | **115 passed in 10.34s**, exit 0 |
| Fresh CI-matching environment, Python 3.13.16 | **115 passed in 10.43s**, exit 0 |
| Ruff | **All checks passed**, exit 0 |
| Ruff formatting | **59 files already formatted**, exit 0 |
| compileall, app/main/tests/examples/tools | Passed, exit 0 |
| Dependency consistency | **No broken requirements found**, exit 0 |
| Existing license inventory | All **11** recorded distributions match installed versions |
| Existing source examples | All **6** baseline SHA-256 values unchanged |

All existing 115 tests remain. Coverage includes worker completion/GUI ownership, signal and runnable release, chained success/error operations, busy-close handling, XLSX handle closure, identifiers/precision, formula protection and text limits. Automatic GC remains enabled. Source tests use Qt offscreen; the packaged-EXE checks below use native Windows dialogs.

## Final EXE from the actual ZIP

`tools/verify_release.py` independently checked the archive and extracted it to `test-output/release/распакованный релиз f72ab2ef/`. The tested extracted EXE has exactly the EXE hash above. `tools/smoke_release.py --exe <extracted executable>` completed **16/16 checks**, with normal shutdown and process exit **0**.

| Scenario | Result |
| --- | --- |
| Main window / CSV import | Native import dialog; six synthetic rows loaded; Cyrillic/spaced paths supported |
| Embedded runtime | Deliberately invalid PYTHONHOME, empty PYTHONPATH, no VIRTUAL_ENV, System32-only PATH; bundled Python/Qt memory mappings verified |
| Remove duplicates / empty rows | Six rows became five, then three; empty and whitespace-only rows removed |
| Trim / CSV export | Cyrillic names trimmed; leading zeros, 40-digit ID, literal NA and exact decimal spelling preserved |
| Undo / Reset | Trim undone; original six rows restored; reset itself undone |
| XLSX export | Leading-zero and long identifiers read back as string cells |
| XLSX import | Second worksheet selected through the picker; its two rows verified via exported CSV |
| Merge | Two CSV files combined; 00010 and 00011 retained |
| CSV formula guard | =1+1 rejected in checked mode; no output file created |
| XLSX literal formula-like text | =1+1 stored as a string, not a formula |
| XLSX long-text guard | 40,000-character cell rejected with the 32,767 limit; no output created |
| CSV long text | All 40,000 characters read back without truncation |
| Input preservation | Six generated input files retained byte hashes |
| Shutdown | Clean close, exit 0 |

The four extracted EXE pages were captured using PrintWindow and visually inspected. Sidebar version **v1.0.1**, title-bar icon, action icons, Modern Dark styling and layouts render correctly. Source README screenshots use Qt widget capture and synthetic example data; overlapping desktop windows are not captured.

Evidence: `test-output/release-1.0.1/build.log`, `pytest311.log`, `pytest31316.log`, `zip-verification.json`, `EXE_RESULTS.json` and `exe-smoke.log`. The original GUI run is `test-output/release/e2e-713913b7/results.json`. Visual captures are `test-output/release/final-*.png`; they are excluded from the binary ZIP.

## Archive contents, confidentiality and licensing

- Independent verification passed ZIP CRC, unique/safe member paths, required runtime, exact manifest membership and every file's SHA-256.
- The portable archive contains the EXE, embedded runtime, application icons, user guide, release notes, MIT license and third-party license/source notices. Keep the whole DataClean folder together.
- No virtual environment, Git metadata, tests, CI helpers, logs, temporary files, CSV/XLSX inputs, user documents or standalone application Python source files are included. Compiled Python code required to run the application is included.
- Targeted scanning of shipped binary/text files and application sources found **0** private-key/OpenAI/GitHub/AWS pattern matches. The inventory was reviewed; only synthetic documents were used in tests. This is a targeted check, not a guarantee against every secret format.
- Existing Python/dependency license versions match the build. The bundle includes LGPLv3/GPL texts, Qt/PySide6 notices, official corresponding-source links, checked upstream archive provenance and compatible shared-library replacement information. Qt remains external shared DLLs. No commercial Qt license is claimed. This is a technical license inventory, not a legal opinion.
- The previous v1.0.0 ZIP remains unchanged. All work and new artifacts stay inside `D:/DataClean`.

## Known limitations and remaining checks

- **The separate Python 3.11 GitHub-hosted Windows access violation remains unexplained and is not claimed fixed by this package.** The current main's lifetime repairs and diagnostic matrix are included. See [CI_STABILITY.md](CI_STABILITY.md). Local source/EXE passes do not establish hosted stability.
- The EXE is unsigned; unknown-publisher/SmartScreen warnings may appear. No Windows security protection was disabled.
- The portable application uses embedded Python 3.13.5. Clean Windows 10/11 machines without Python, real Excel/LibreOffice, high-DPI/multi-monitor and large-file stress cases remain additional distribution checks. Local testing covered Windows 11 10.0.26200.
- CSV has no cell types and spreadsheet opening can reinterpret ordinary IDs/numbers. Checked export blocks suspicious formulas without rewriting values. XLSX import retains pandas inference; lost precision cannot be recovered.
- Data and undo snapshots must fit in RAM. There is no task cancellation or workbook-format/macro/chart preservation.

This is a locally prepared **1.0.1** update for review and testing. The project was not pushed and no GitHub Release was published.
