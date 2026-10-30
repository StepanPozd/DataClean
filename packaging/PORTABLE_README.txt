DataClean 1.0.0 — Windows x64 portable release
Developer: Stepan Pozdnyakov

1. Extract the complete DataClean folder from the ZIP to a writable location.
2. Open DataClean.exe. Keep the _internal folder next to the executable.
3. Import a CSV or XLSX file, clean the working copy and export to a new filename.

Python and application dependencies are included. No Python installation,
administrator privileges, system installation or account is required.
Supported target: Windows 10/11 x64 with the native Windows ICU API.

CSV import defaults to Text to preserve leading zeros, NA/NULL and precise text.
CSV export can block formula-like values. CSV itself has no cell types: use XLSX
to retain text types when opening results in a spreadsheet.
XLSX text exceeding 32,767 characters is rejected; it is never truncated.
Original input files remain protected. Export before closing to keep changes.

This executable is NOT digitally signed. Windows may show an unknown-publisher
or SmartScreen warning. No security protection needs to be disabled by DataClean.
The application contains no telemetry, advertising, auto-updater or network API.

Read LICENSE, THIRD_PARTY_NOTICES.md and LICENSES/ for copyright and license terms.
DataClean uses Qt/PySide6 and Shiboken under LGPLv3; compatible shared libraries
can be replaced. Corresponding source references and instructions are provided
in THIRD_PARTY_NOTICES.md and LICENSES/UPSTREAM-SOURCES.json.

Planned release page (not necessarily published):
https://github.com/StepanPozd/DataClean/releases
Contact: step45970@gmail.com
