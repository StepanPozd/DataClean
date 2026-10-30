# Windows Python 3.11 crash — investigation still open

Release follow-up: **v1.0.1 now packages the current main code**, including the lifetime changes and diagnostic/test updates. See [PACKAGING_REPORT.md](PACKAGING_REPORT.md) for the separate local build/EXE evidence. The hosted-crash investigation remains open; earlier statements about not rebuilding describe the diagnostic tasks below.

## Follow-up after hosted failure of bf3ca37 — 2026-10-30

**Status: the recurring hosted-runner crash is not explained or proven fixed.** The previous local success and worker-lifetime repair were insufficient. The earlier investigation below is retained as history, not evidence that the current Actions failure is resolved.

### Actual remote environment recovered

The full logs of [run 41011588867](https://github.com/StepanPozd/DataClean/actions/runs/41011588867), commit `bf3ca37`, were retrieved read-only using the existing GitHub sign-in. No credentials were printed or stored in the project. Raw logs stay under ignored `test-output/ci-deep/`.

- Python 3.11 job: **3.11.9**, CPython tag `de54cf5`, MSC 1938, Windows x64. It crashes during worksheet selection, with GC active in the worker inside openpyxl style parsing. The earlier lifetime tests have not yet run at that point.
- Runner: **Windows Server 2025**, image `windows-2025-vs2026`, version **20261021.278.1**. Local OS remains Windows 11 10.0.26200; these are not identical operating environments.
- Python 3.13 job: **3.13.16**, not the previously tested local 3.13.5. It passed the worksheet-selection test and reached later worker tests before cancellation; its complete result is unknown.
- Every one of the **19 packages in the remote Python 3.11 freeze matches the previous local 3.11 freeze**, after normalizing distribution names. A package-version mismatch is therefore excluded as the sufficient explanation for this run. `pip freeze` does not establish identical OS DLLs, scheduling, bootstrap tools or allocation history.

| Distribution | Actual remote Python 3.11 | Actual remote Python 3.13 |
| --- | --- | --- |
| PySide6-Essentials / shiboken6 | 6.12.0 / 6.12.0 | 6.12.0 / 6.12.0 |
| pandas / openpyxl | 3.1.0 / 3.1.5 | 3.1.0 / 3.1.5 |
| NumPy | 2.4.6 | 2.5.4 |
| pytest / pytest-qt | 9.2.0 / 4.5.0 | 9.2.0 / 4.5.0 |
| Remaining packages | charset-normalizer 3.5.2, colorama 0.4.6, et-xmlfile 2.0.0, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0, python-dateutil 3.0.0, Ruff 0.17.3, six 1.17.0, typing-extensions 4.16.0, tzdata 2026.6 | Same versions |

Fresh project-local virtual environments were created with the official portable Python NuGet runtimes: `.cache/ci-deep311-612/` and `.cache/ci-deep313-612/`. The Python patch versions and all 19 frozen application/test dependencies match the respective remote jobs. Two additional Python 3.11 environments replace **only PySide6-Essentials and shiboken6 together** with 6.11.3 or 6.10.3. All other 17 versions stay identical; the inventories were compared programmatically. No installed system Python or Windows configuration was changed.

### New experiments and their limits

| Experiment on local Windows | Qt 6.12.0 | Qt 6.11.3 | Qt 6.10.3 |
| --- | --- | --- | --- |
| Fresh Python 3.11.9, original full suite/order | **10 × 115 passed** | **3 × 115 passed** | **3 × 115 passed** |
| Original worksheet-selection test in separate processes | **5/5 passed** | **5/5 passed** | **5/5 passed** |
| `gc.collect()` before every worker body, full suite | **115 passed** | **115 passed** | **115 passed** |
| More frequent automatic GC, thresholds `(50, 5, 5)`, full suite | **115 passed** | **115 passed** | **115 passed** |
| Retire 150 real GUI trees and collect their Python cycles in a shared pool thread | Completed, GC enabled | Completed, GC enabled | Completed, GC enabled |

Python **3.13.16** with its exact remote 19-package freeze also completed **3 × 115 tests**. A separate Qt 6.12.0 / Python 3.11 import-overlay experiment selecting **pytest-qt 4.4.0** instead of 4.5.0 completed **115 tests**; this single successful control does not prove that 4.5.0 is defective. No version has been changed in the application's runtime requirements.

The separated groups on Python 3.11 / Qt 6.12 completed **82 core tests** and **33 GUI tests**; their union is the complete 115-test suite. No test is removed from the normal full-order run.

One local instrumented full run recorded **79 worker entries and 79 GUI releases**, **44 worker-thread GC starts**, and **no off-GUI destruction of the tracked windows/signal carriers**. The journal observes selected objects, not every internal Qt allocation. Its timing perturbation and successful local result cannot exclude a race on the hosted runner.

### Object-lifetime audit

- The existing model instances and signal carriers have QObject parents. Workers are joined before disposal, and queued results are delivered to GUI slots. These repairs still have regression coverage, but the hosted failure demonstrates they are not a sufficient explanation/fix for the crash.
- `waitForDone()` terminates pool threads; the pool object itself is reused. Holding Python wrappers from `QThread.currentThread()` beyond that join is unsafe bookkeeping. The two tests that retained such wrappers now store `threading.get_ident()` integers instead, preserving their GUI-versus-worker assertions.
- A separate experiment calling `objectName()` on a retired thread wrapper produced native access violations on Qt 6.12.0 and 6.10.3 in individual runs, despite `shiboken6.isValid()` reporting true; other repeats succeeded. This is a **different, deliberately invalid-lifetime operation**, not reproduction of the hosted openpyxl/GC stack. The affected tests run **after** the failing worksheet test and therefore cannot explain the earlier crash by execution order alone.
- `tools/probe_qt_thread_lifetime.py` provides a small Qt-only probe without DataClean, pytest-qt or openpyxl. Its default mode only records metadata. `--invoke-retired-method` deliberately calls across the lifetime boundary and may crash its process; it is not a CI application gate. The small probe passed its first local runs, so equivalence to the larger failing probe is not established.
- Workbook-close `finally` blocks and four existing success/error close tests remain intact. No evidence justifies changing Excel parsing or data processing.

Upstream [Shiboken ownership documentation](https://doc.qt.io/qtforpython-6.11/shiboken6/typesystem_ownership.html) distinguishes Python wrapper and C++ instance lifetimes. [Qt thread-affinity rules](https://doc.qt.io/qt-6/threads-qobject.html) still apply. The [6.11.1 release notes](https://doc.qt.io/qtforpython-6/release_notes/pyside6_release_notes.html) describe PYSIDE-3288 deferred owner-thread deletion support; this documents relevant machinery, not proof that the current crash is that upstream issue.

**Confirmed:** hosted failure after bf3ca37; identical 3.11 package versions; interpreter-patch mismatch in the old 3.13 comparison; unsafe retained-thread-wrapper bookkeeping. **Not confirmed:** the exact native corruption site, a Qt 6.12-only regression, pytest-qt 4.5 as the cause, or that the previous worker race caused this particular hosted failure. No downgrade or production GC policy is justified by the current evidence.

### Diagnostic CI changes and next experiment

The workflow now sets **`strategy.fail-fast: false`** and runs four independent entries: Python 3.11.9 / Qt 6.12.0, Python 3.13.16 / Qt 6.12.0, and Python 3.11.9 with Qt 6.11.3 and 6.10.3. `.github/ci-constraints.txt` fixes the common packages to the recovered remote versions; NumPy and the matched Qt/Shiboken pair are explicit matrix pins. The application's flexible runtime requirements remain unchanged.

Before tests, `tools/ci_diagnostics.py` prints and saves Python/platform details, the requested core package versions, all installed versions, Qt runtime, GC settings, CPU count and a small whitelist of runner image metadata. It does not dump environment variables or document contents.

Each entry executes:

1. The complete suite in a fresh process **without journal hooks**, preserving the original order.
2. The complete suite with an opt-in GC/Qt lifetime journal.
3. Core and GUI groups in separate processes.
4. Five separate runs of the original worksheet-selection test.

Later diagnostic steps use `if: !cancelled()` to gather evidence after a failed step; **they do not erase its failure**. There is no `continue-on-error`, skip or xfail. The subprocess runner returns a nonzero overall status if any child fails or times out, even if later iterations pass. A deliberate invalid-argument child returned pytest exit 4 and the driver correctly returned 1.

The journal uses immediate JSONL appends for test phases, GC starts/stops and thread IDs, worker entry/exit, GUI join/release, tracked QObject destruction and wrapper finalization. It does not collect garbage, flush deferred deletion or alter application ownership. Normal testing does not load the plugin. Log/JUnit/environment/install evidence is uploaded with `if: always()` and a 14-day retention; test documents and native memory dumps are not requested.

Run locally, for example:

```powershell
.\.cache\ci-deep311-612\Scripts\python.exe tools/ci_diagnostics.py --group full --output test-output/ci/full
.\.cache\ci-deep311-612\Scripts\python.exe tools/ci_diagnostics.py --group full --journal --output test-output/ci/journal
.\.cache\ci-deep311-612\Scripts\python.exe tools/ci_diagnostics.py --group excel --repeat 5 --journal --output test-output/ci/excel
```

**Next required experiment:** after the owner pushes this diagnostic commit, compare all four hosted matrix entries and preserve the full-run failure plus the journal artifacts. If only 6.12 fails repeatedly with matched other packages, that supports a version interaction; if only full-order runs fail while isolated groups pass, bisect the preceding test prefix in additional diagnostic runs while retaining the full suite as a required gate. If instrumentation changes the result, compare the last GC and QObject events rather than treating a journaled pass as a fix. A native stack/minimal reproducer on the same Server 2025 image remains necessary if those records cannot identify the destroyed object.

After the thread-ID test cleanup, final uninstrumented full runs passed **115/115 in all four local matrix environments**; final journaled full runs passed **115/115** on Python 3.11.9 and 3.13.16 with Qt 6.12.0. Ruff, formatting and compileall passed on both exact Python versions, and dependency consistency passed. The workflow YAML was parsed locally and its four matrix entries, fail-fast setting and absence of continue-on-error checked; it was not executed remotely.

The current commit is **diagnostic, not a claim of hosted stability**. No push, workflow dispatch, publication or EXE rebuild was performed. Existing release hashes and source examples are unchanged. Detailed local evidence is under ignored `test-output/ci-deep/`; raw credentials are not part of those artifacts.

---

# Previous local investigation — superseded for hosted-crash conclusions

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
