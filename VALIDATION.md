# Local validation — worker lifetime and Windows CI

**Hosted-runner status update, 2026-10-30:** commit bf3ca37 still crashed on Python 3.11.9 in Actions run 41011588867. The local results below do not establish a hosted fix. A follow-up compared all 19 actual remote dependency versions, built matching environments, tested Qt 6.12.0/6.11.3/6.10.3, removed retained pooled-thread wrappers from two tests, and added independent CI/version/GC diagnostics. See the latest section of [CI_STABILITY.md](CI_STABILITY.md); the native hosted failure remains unexplained. No application business logic or release binary was changed in this follow-up.

Validation date: **2026-10-30**. The current source suite has **115 tests**, including all previous 104 and 11 worker-lifetime/workbook-close regression cases. Python **3.11.9** and **3.13.5** each passed **10 consecutive full-suite runs**, Ruff, formatting, compileall and dependency consistency. Native source launches on both interpreters imported XLSX, trimmed data and closed with zero active workers and exit 0. After 100 success/error tasks, a separate reference-release probe found zero retained workers or signal wrappers on both versions.

The original Python 3.11 implementation reproduced an intermittent native access violation during worker-thread garbage collection on the third repeated full-suite run. Event-gated regression tests also deterministically exposed premature task release in both success and error paths. Explicit GUI ownership, joining before completion callbacks and coordinated fixture teardown fix that race without disabling GC, excluding tests or removing Python 3.11. The unchanged original XLSX worksheet-selection test passed 60 repetitions on each interpreter, including 30 worker-GC cases.

See [CI_STABILITY.md](CI_STABILITY.md) for versions, before/after evidence, repeat-run results and the limits of the native-crash diagnosis. The existing v1.0.0 EXE/ZIP below were **not rebuilt**; these latest results describe the updated source code. A hosted Actions run after the owner's push remains necessary. No push was performed during this fix.

---

# Windows release validation — earlier stage

Validation date: **2026-10-30**. The latest release verification supersedes the totals below while preserving the earlier data-safety evidence.

| Check | Actual result |
| --- | --- |
| Complete pytest suite after packaging | **104 passed in 6.89s**, exit 0; all previous 101 plus 3 resource tests |
| Ruff / format / compileall / pip check | All passed |
| Final EXE from the extracted release ZIP | **16/16 GUI checks passed**, normal exit 0 |
| Embedded runtime | Python/Qt DLLs loaded from the extracted application, no `.venv`; invalid PYTHONHOME and System32-only PATH |
| Interface/resources | Four native EXE pages captured using PrintWindow and visually inspected; dark styling and icons present |
| ZIP integrity | CRC, complete manifest SHA-256, structure and required runtime passed |
| Secret checks | 0 matches for targeted private-key/OpenAI/GitHub/AWS patterns in shipped files and application source |
| Source protection | 6/6 existing example hashes and 6/6 generated EXE-test input hashes unchanged |

The release ZIP is `release/DataClean-v1.0.0-win64.zip`, **58,023,955 bytes**, 1,096 files. SHA-256: `6263f13d9a5aa6a8cee8a19b3db57fa2ea6bd077da92a7312e3308ed35b6984c`.

Native final-EXE results: `test-output/release/e2e-b4adf707/results.json` and `last-success.json`. They cover CSV/XLSX import/export, worksheet selection, identifiers/precision, duplicate/empty-row removal, trimming, Undo/Reset, merge, formula protection, long-text rejection, complete long CSV text, Cyrillic/spaced paths and shutdown. Tests used their own synthetic documents. Evidence stays local and is excluded from the distribution.

The QtCore startup DLL error was traced to an incompatible Poppler ICU selected during packaging. Isolated build PATH and dependency filtering fixed it; the final EXE uses native Windows ICU. No business logic changes were needed for packaging or GUI automation.

See [PACKAGING_REPORT.md](PACKAGING_REPORT.md) for exact versions, hashes, commands, GUI evidence and license inventory. The EXE is **unsigned**. Clean Windows 10/11 machines without Python, real Excel/LibreOffice, high-DPI combinations and large-file stress remain additional checks; the local native environment was Windows 11 10.0.26200 x64. No GitHub publication occurred.

---

# Data-safety validation — earlier stage

Validation date: **2026-10-29**. This historical stage records the data-safety changes, superseding the earlier 56-test validation; the current release totals are above.

## Environment

- Windows x64, Python 3.13.5 in the project-local `.venv`.
- PySide6-Essentials 6.12.0, pandas 3.1.0, openpyxl 3.1.5.
- Installed versions remain recorded in `requirements-lock.txt`; no dependency changes were needed.

## Executed checks

All commands ran from `D:\DataClean` with `.venv\Scripts\python.exe`.

| Check | Command | Actual result |
| --- | --- | --- |
| Original test suite, before changes | `-m pytest tests/test_processing.py tests/test_files.py tests/test_ui.py -q --tb=short` | **56 passed in 3.74s**, exit 0 |
| Original test suite, after code changes | Same command | **56 passed in 3.74s**, exit 0 |
| New data-safety tests | `-m pytest tests/test_data_safety.py tests/test_data_safety_ui.py -q --tb=short` | **45 passed in 2.58s**, exit 0 |
| Complete suite | `-m pytest -q --tb=short` | **101 passed in 6.09s**, exit 0 |
| Static analysis | `-m ruff check .` | **All checks passed!**, exit 0 |
| Formatting | `-m ruff format --check .` | **33 files already formatted**, exit 0 |
| Byte compilation | `-m compileall -q app main.py tests examples tools` | No errors, exit 0 |
| Dependency consistency | `-m pip check` | **No broken requirements found.**, exit 0 |
| Native application launch | Timed script calling the actual `main.main()` entry point | One visible MainWindow, correct empty state, exit 0 |
| Native CSV import dialog | Display, change interpretation, capture widgets | Text selected by default; Auto selectable; three captures saved |
| Source examples | SHA-256 before/after changes and tests | **6 of 6 unchanged** |

GUI tests use Qt offscreen. The native smoke check ran separately using the Windows Qt platform; the window and both dialog states were captured in ignored `test-output/data-safety/` and visually inspected. The Modern Dark styling remains intact. File-picker responses and confirmations are controlled in GUI tests; native OS save/open dialogs were not manually clicked through.

## Verified data-safety fixes

### XLSX text limits

- Values containing 32,766 or 32,767 Cyrillic characters export and read back without shortening or warnings.
- Values containing 32,768 or 40,000 characters are rejected with their positional row and column, the 32,767-character limit and a suggestion to use CSV.
- Headers are checked too, including a header-only dataset with an oversized column name.
- Validation runs before temporary-file creation. Tests substitute the temporary-file factory to ensure it cannot be reached for invalid long text.
- Rejection creates no new output, leaves an existing destination intact and does not mutate the DataFrame.
- Long text exceeding Excel's limit can be exported completely to CSV when it satisfies the chosen CSV policy.
- GUI failures do not mark changes as saved or display success; controls recover and history records the failed action.

### CSV interpretation

- The import dialog defaults to **Text — preserve values**. Automatic encoding detection and automatic type detection are separate choices.
- Text-mode tests preserve `00123`, `00045`, literal `NA`, `NULL`, `NaN`, `N/A`, lowercase null-like tokens, a 40-digit identifier, an integer beyond binary64's exact range, long decimal text, trailing decimal zeros, exponent notation, whitespace and Cyrillic text.
- Text-mode cases run with UTF-8 BOM, Windows-1251 and UTF-16. Original source bytes/hashes remain unchanged.
- Empty fields, completely blank records and short records remain empty strings, without null-token or number inference. Empty strings therefore do not contribute to pandas missing-value counts.
- Explicit Auto mode retains historical numeric/missing-value behavior. The unchanged original test suite also verifies that compatibility.
- UI tests verify that the selected mode reaches the worker and history, survives an encoding retry and applies to each merge source. Merged identifiers retain leading zeros in the default dialog mode.
- Text-mode CSV imported and exported to XLSX retains string cell types, exact identifiers/decimal spelling, literal null tokens and formula-like strings. This check reads the exported workbook with openpyxl to inspect the stored values/types, independently of pandas' XLSX import inference.

### CSV export policy

- Default `csv_mode="spreadsheet"` rejects potentially formula-like text in both headers and data before writing.
- Tested prefixes: `=`, `+`, `-`, `@`, tabs, CR/LF, leading whitespace, BOM/zero-width prefixes, apostrophe-prefixed formulas and full-width equivalents. Text `-12` is conservatively rejected; actual negative numeric values remain allowed.
- CSV quoting correctly preserves embedded separators, quotes and line breaks inside a field; a formula marker later inside the same quoted field is not treated as a separate cell by the CSV round-trip test.
- A rejected checked export leaves the frame and an existing output unchanged. Invalid policy names are rejected.
- Explicit `csv_mode="raw"` preserves formula-like values, headers, quotes, whitespace and newlines without added escape prefixes.
- The UI offers both policies in the save dialog and explains before either CSV export that CSV has no cell types. Raw export additionally warns that formula checks are disabled and requires explicit confirmation. Declining creates no file and retains the unsaved state.
- History records the chosen CSV policy. Both modes export current field values without silently prefixing, stripping or replacing data.

## Existing regression coverage retained

The original 56 tests were not rewritten. They continue to cover statistics, duplicate/empty-row removal, trim/fill, Undo and Reset, saved-state tracking, encoding and separator detection, Cyrillic paths, multi-sheet XLSX import, merge compatibility/reordered columns, CSV/XLSX export, source-path/hard-link protection, overwrite confirmation, failure recovery, navigation, minimum window size and worker-to-GUI thread delivery.

## Limits of this verification and remaining work

- **CSV cannot promise type preservation when opened directly in a spreadsheet.** Checked export blocks suspicious formulas; it does not neutralize every possible spreadsheet behavior or subsequent save/reopen workflow. Raw export deliberately disables that protection. For exact text types use XLSX or explicitly import CSV columns as Text.
- CSV serialization does not encode every DataFrame distinction, such as null versus an empty string. Text import preserves CSV field spelling, rather than all metadata of a prior DataFrame or the original file's quoting/bytes.
- Auto CSV import can still change identifiers and precision when explicitly selected. The core `read_file` API retains its historical Auto default; programmatic callers must pass `csv_mode="text"` for preservation. The existing XLSX importer also still uses pandas type inference. Exporting strings to XLSX stores them literally, but this does not change how a future XLSX import infers types.
- Already-converted numeric values cannot regain lost precision. Precision-sensitive identifiers/decimals must stay text from their first import onward. Numeric Excel cells still have Excel's precision limits.
- Streaming/chunked processing, per-column type configuration, cancellation of a running task, persistent sessions and an installer are outside this change. Datasets must fit in RAM; Undo's budget is soft.
- Local execution covered Python 3.13.5 only. Other Python/Qt versions, high-DPI/multi-monitor combinations, large-file stress cases and real Excel/LibreOffice automation were not exercised. The CI workflow was not published or run remotely.
- `REVIEW_REPORT.md` is marked as a historical pre-fix report. The older external review ZIP was not modified or rebuilt; current code and this report are inside `D:\DataClean`.

No GitHub publication or push was performed. Changes were confined to the project directory, and no existing user documents were used as test inputs or modified.
