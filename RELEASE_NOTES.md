# DataClean 1.0.1

Prepared locally on **2026-10-30** from `main` at `37670b6`, including the Qt worker-lifetime changes from `bf3ca37` and the current test/CI diagnostics. Not published to GitHub.

## Changes from 1.0.0

- Retain each background task until QThreadPool has completed it, before enabling the next action or closing the window.
- Explicit queued GUI callbacks, window-owned signal objects, GUI-thread disposal of completed runnables and release of task closures.
- Coordinated GUI-test teardown, resource-release regression coverage and thread-ID assertions that do not retain retired QThread wrappers.
- Application, sidebar and Windows EXE metadata now report **1.0.1**.
- Modern Dark styling, CSV/XLSX workflows, Undo/Reset, merge and existing data-protection policies are preserved. No new user-facing features or dependency upgrades.

## Validation scope

See `PACKAGING_REPORT.md` in the source project for actual v1.0.1 build, source tests, packaged-EXE checks and archive hash. The independent **Python 3.11 GitHub-hosted Windows crash remains unproven as fixed**; the diagnostic matrix and GC journal are retained. This release packages the current main code, without claiming that every native race has been eliminated.

The portable EXE remains unsigned. Clean-machine Windows 10/11, high-DPI and real Excel/LibreOffice checks remain additional distribution checks. Keep the entire extracted application folder, including `_internal` and license notices.

---

# DataClean 1.0.0 — previous local package

Prepared locally on **2026-10-30** for a future Windows x64 GitHub Release. This document does not mean a release has been published.

## Portable Windows application

- `DataClean.exe` runs as a windowed desktop application, with no console window and no separate Python installation required.
- PyInstaller onedir layout: keep the complete `DataClean/` folder, including `_internal/`.
- Multi-resolution application icon (16–256 px), 512 px PNG and editable SVG source.
- Modern Dark interface with Dashboard, Data Editor, Merge Files and History.

## Data workflows

- Import CSV and XLSX, choose a worksheet and select CSV encoding/interpretation.
- Preserve leading zeros, literal `NA`/`NULL`, long identifiers and exact decimal spelling with the default Text import mode.
- Remove duplicate and empty rows, trim text and fill missing values; undo actions or reset to the original import.
- Merge files by matching column names, preview the result and export it or continue cleaning.
- Export UTF-8 BOM CSV and XLSX; protect original inputs and confirm replacement of other outputs.
- Reject XLSX text beyond 32,767 characters before writing; no automatic truncation.
- Block formula-like CSV fields by default; unprotected export is an explicit, warned choice without silent value rewriting.
- Background workers keep file operations and transformations off the GUI thread.

## Packaging and notices

- Embedded CPython, pandas, openpyxl and required PySide6 components.
- Only Qt Core, Gui, Widgets and Svg, with required Windows/icon/image plugins; no WebEngine or QML runtime.
- Build PATH isolation prevents unrelated tool installations from supplying incompatible DLLs.
- No UPX, installer, startup registration, analytics, advertising, telemetry or application network calls.
- MIT application license, LGPLv3 Qt/PySide6 notices, third-party license files and corresponding-source references included.

## Known limitations

- **Unsigned executable:** unknown-publisher or SmartScreen warnings may appear. No signing claim is made.
- Target: Windows 10/11 x64 with native Windows ICU support; other architectures and older Windows releases are not supported.
- CSV does not carry cell types. Direct spreadsheet opening can still reinterpret values; use XLSX or import columns as Text.
- XLSX import still uses pandas type inference. Already-converted numeric values cannot recover lost precision.
- Working datasets and undo snapshots must fit in RAM. There is no task cancellation, persistent session recovery or direct cell editing.
- Excel workbook formatting, macros, charts and formulas are not retained as a workbook-preservation feature.
- A clean Windows VM without Python and real Excel/LibreOffice automation remain additional release checks; local testing details are recorded in the source repository's `PACKAGING_REPORT.md`.

Developer: **Stepan Pozdnyakov** · [GitHub](https://github.com/StepanPozd) · [step45970@gmail.com](mailto:step45970@gmail.com)

Planned release page: [StepanPozd/DataClean Releases](https://github.com/StepanPozd/DataClean/releases). Nothing is uploaded automatically.
