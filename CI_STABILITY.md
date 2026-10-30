# Windows Python 3.11 worker-lifetime investigation

Validation date: **2026-10-30**. Baseline: `0b0d6ec` (`Initial release - DataClean v1.0.0`). This is a source fix; the existing v1.0.0 EXE and ZIP were not rebuilt.

## Reproduction and diagnosis

The public [Actions run 41008924740](https://github.com/StepanPozd/DataClean/actions/runs/41008924740) reports failure for Python 3.11 and success for 3.13. Its raw job logs require authentication (the API returned HTTP 403), so the exact remote package freeze could not be independently recovered. The reported remote stack was in `excel_sheets()` / openpyxl while garbage collection was active.

Python **3.11.9 x64** was extracted from the official [Python NuGet package](https://www.nuget.org/packages/python/3.11.9) under project-local `.cache/ci-python311/`, without installing Python into Windows or changing the registry/PATH. Dependencies were freshly resolved from the same `requirements-dev.txt` used by Actions. The local comparison environment was Python **3.13.5 x64** on Windows 11 10.0.26200.

| Component | Python 3.11 environment | Python 3.13 environment |
| --- | --- | --- |
| PySide6-Essentials / Shiboken | 6.12.0 | 6.12.0 |
| pandas | 3.1.0 | 3.1.0 |
| NumPy | 2.4.6 | 2.5.4 |
| openpyxl | 3.1.5 | 3.1.5 |
| pytest / pytest-qt | 9.2.0 / 4.5.0 | 9.2.0 / 4.5.0 |
| Ruff | 0.17.3 | 0.17.3 |

Before changes, the full 104-test suite passed once on each interpreter. A repeated Python 3.11 series then passed twice and **crashed on its third full run with exit 0xC0000005 (3221225477)**. The local fault stack showed `Garbage-collecting` inside the pool thread, with `csv.Sniffer._guess_delimiter -> read_file -> prepare -> TaskWorker.run`; the GUI thread was in pytest-qt's event-loop wait. This reproduces the native failure class without openpyxl being the active parser. The Python frame describes where collection was triggered, rather than proving that parser caused memory corruption.

The original XLSX worksheet-selection test passed in isolation and in **60 actual parametrized repetitions** (30 ordinary and 30 calling `gc.collect()` in the worker). This explains why a single targeted pass does not establish suite stability. The first attempted duplicate-node command collected only one test and is not counted as repetition evidence.

Code inspection found a concrete lifetime race:

1. A worker emits a queued success/error signal before `run()` has returned. The GUI may receive it while the runnable is still executing.
2. Both completion slots immediately dropped `_worker`, set `busy=False` and invoked the next operation. The old pool job could still be active at that point.
3. `QRunnable` auto-deletion was enabled. Python closures owned by it could be released from a pool thread. The signal carrier was a parentless QObject created in the GUI thread; completion callbacks were also retained on the window after completion, including closures/bound methods referring to the window.
4. GUI fixtures waited for `busy=False`, which did not guarantee pool completion, before closing widgets. pytest-qt schedules widget destruction separately. Later worker allocations could trigger collection of surviving Python/Qt cycles.

The race is confirmed independently of the intermittent crash: a new event-gated regression test was copied onto the original application code and **failed in both success and error cases**, because its GUI callback ran before the runnable returned. It passes with the fix. No fixed sleeps are used to make that assertion.

The best-supported explanation for the access violation is unsafe cleanup timing involving Qt/Python object ownership and worker-triggered collection. The exact native instruction/use-after-free was not identified with a C++ debugger, so a particular upstream PySide6 or CPython defect is **not** claimed as proven.

## Minimal lifetime fix

- `TaskWorker` disables runnable auto-deletion and gives its signal QObject the owning window as parent. The window retains the worker until completion is joined.
- Success/error connections explicitly use queued delivery to GUI slots.
- Completion calls `QThreadPool.waitForDone()` before releasing the worker, setting the window idle or running user callbacks. The work function has already returned when the signal is emitted; the join covers its emission/return tail. Worker functions must not synchronously wait for a GUI callback.
- Both callback references and the worker's function closure are cleared in the GUI thread. The signal carrier is disposed with `deleteLater()`.
- After joining, the C++ runnable is explicitly disposed in the GUI thread with `shiboken6.delete()`. Inspection showed that PySide6 retains non-auto-deleting runnable wrappers under their pool: the initial candidate retained 100/100 workers/signals after 100 operations. Explicit disposal reduced both counts to **0/100** on each interpreter. A new weak-reference regression covers this cleanup so the race fix does not introduce unbounded retention.
- Accepted window close also joins its pool. Busy operations continue to reject close as before.
- A shared fixture cleanup waits for both idle/batch completion and actual pool termination, including pytest-qt's `before_close_func` path.

These rules follow Qt's documented [QRunnable ownership](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QRunnable.html), [QThreadPool completion](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThreadPool.html), [QObject thread-affinity/deletion constraints](https://doc.qt.io/qt-6/threads-qobject.html), and [Shiboken explicit C++ deletion](https://doc.qt.io/qtforpython-6/shiboken2/shibokenmodule.html).

Workbook ownership was checked separately: `excel_sheets()` and the XLSX header inspection in `read_file()` already close returned workbooks in `finally`; pandas manages its own subsequent Excel reader. New tests check explicit close both on success and when metadata access raises, and rename the file afterward on Windows. No openpyxl code or parsing behavior was changed.

Automatic GC remains enabled. No tests were skipped/xfail'ed, no interpreter was removed, and no dependency was downgraded or pinned to conceal the failure. The CI matrix still includes 3.11 and 3.13; it now logs resolved versions and uses verbose pytest with early faulthandler activation to make any future native failure easier to locate.

## Verification

The original **104 tests** remain, plus **11 regression cases**:

- Two event-gated completion cases (success/error), checking ownership while joining, GUI callback thread, closure release, pool idle and signal destruction on the GUI thread.
- Two cases starting a follow-up task from a success/error callback.
- One case checking that twenty completed success/error tasks leave no retained workers or signal wrappers.
- One case performing ten real two-stage XLSX imports with explicit worker-thread collection and automatic GC enabled; selected-sheet values, source bytes and file-handle release are checked.
- One case rejecting close while work is active, then closing cleanly after completion.
- Four workbook-close cases: sheet listing/import metadata, each succeeding/failing.

| Executed check | Actual result |
| --- | --- |
| Original app + new event-gated regression | **2 failed**, demonstrating the race |
| Ownership fix before fixture/test changes | **10 consecutive full runs × 104 passed** on Python 3.11 |
| Final full suite, Python 3.11 | **10 consecutive full runs × 115 passed**; last run 8.62s |
| Final full suite, Python 3.13 | **10 consecutive full runs × 115 passed**; last run 8.68s |
| Original worksheet-selection test in isolation after fix | **1 passed** on each interpreter (0.86s / 0.89s) |
| Original worksheet-selection test after fix | **60/60 passed per interpreter**, including 30 worker-GC cases |
| Reference-release probe, both interpreters | 50 success + 50 error tasks; **0 surviving workers and 0 signal wrappers** |
| Ruff, formatting, compileall, dependency consistency | Passed on both Python versions |
| Native source entry point, both Python versions | Visible window, XLSX import, trim, zero active workers, normal close and exit **0** |

Local evidence is excluded from Git under `test-output/ci-crash/`: `baseline311-suite-03.log`, `baseline-race-regression.log`, `ownership311-repeats.json`, `verified311-suite-*.log`, `verified313-suite-*.log`, `verified311-excel-repeat.log`, `verified313-excel-repeat.log`, `verified311-repeats.json`, `verified313-repeats.json`, `references311.log`, `references313.log`, `python311-freeze.txt`, `python313-freeze.txt` and native smoke logs. Earlier `final311*` / `final313*` logs describe the intermediate 114-test candidate, before explicit C++ disposal and its regression case. The repetition harness calls the original XLSX test function with pytest parametrization; its observed collection count is 60, not a repeated-node argument count.

To repeat the main checks with an available Python 3.11 interpreter and project-local test environment:

```powershell
py -3.11 -m venv .cache\venv311
.\.cache\venv311\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.cache\venv311\Scripts\python.exe -X faulthandler -m pytest -q tests/test_ui.py::test_excel_import_selects_chosen_sheet tests/test_worker_lifetime.py
foreach ($iteration in 1..10) {
    & .\.cache\venv311\Scripts\python.exe -X faulthandler -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "pytest failed on run $iteration" }
}
```

Use the equivalent Python 3.13 environment for the other matrix entry. Repeated local tests substantially increase confidence, but cannot guarantee absence of every native race on every Windows/Qt combination. A new GitHub Actions run after the owner's push is still needed to validate the hosted runner itself. No push or workflow dispatch was performed during this fix.
