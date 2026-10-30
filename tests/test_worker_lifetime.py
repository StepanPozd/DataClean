"""Regressions for result delivery racing QRunnable completion and Qt cleanup."""

import gc
import weakref
from threading import Event, get_ident

import pandas as pd
import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QThread, Slot
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

import app.ui.main_window as window_module
from app.core.file_handler import excel_sheets
from app.ui.main_window import MainWindow
from app.workers.task_worker import TaskWorker
from main import create_application


@pytest.fixture
def worker_window(qtbot, finish_window):
    create_application([])
    widget = MainWindow()
    qtbot.addWidget(widget, before_close_func=finish_window)
    yield widget
    finish_window(widget)
    widget.close()


class DestructionRecorder(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.threads = []

    @Slot()
    def record(self):
        self.threads.append(QThread.currentThread())


@pytest.mark.parametrize("fails", [False, True])
def test_result_waits_for_runnable_return(worker_window, qtbot, monkeypatch, fails):
    release = Event()
    returned = Event()

    class DelayedReturnWorker(TaskWorker):
        def run(self):
            super().run()
            release.wait(5)
            returned.set()

    monkeypatch.setattr(window_module, "TaskWorker", DelayedReturnWorker)
    original_join = worker_window.pool.waitForDone
    joined = []
    calls = []
    recorder = DestructionRecorder(worker_window)

    def work():
        if fails:
            raise ValueError("expected worker failure")
        return 42

    def join():
        joined.append((QThread.currentThread(), worker_window._worker is worker))
        assert not worker.autoDelete()
        assert shiboken6.isValid(worker.signals)
        assert worker.signals.parent() is worker_window
        release.set()
        return original_join()

    def done(value, *duration):
        calls.append((value, returned.is_set(), QThread.currentThread()))

    monkeypatch.setattr(worker_window.pool, "waitForDone", join)
    try:
        worker_window.run_task("Lifetime regression", work, done, done)
        worker = worker_window._worker
        worker.signals.destroyed.connect(recorder.record)
        qtbot.waitUntil(lambda: bool(calls), timeout=10000)
        assert calls[0][1], "GUI released the task while QRunnable.run() was still active"
        assert calls[0][2] == QApplication.instance().thread()
        assert joined == [(QApplication.instance().thread(), True)]
        assert not shiboken6.isValid(worker)
        assert worker.function is None
        assert worker_window._worker is None
        assert worker_window._on_success is None and worker_window._on_error is None
        assert not worker_window.busy and worker_window.pool.activeThreadCount() == 0
        if fails:
            assert isinstance(calls[0][0], ValueError)
        else:
            assert calls[0][0] == 42
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert not shiboken6.isValid(worker.signals)
        assert recorder.threads == [QApplication.instance().thread()]
    finally:
        release.set()
        original_join(10000)
        monkeypatch.setattr(worker_window.pool, "waitForDone", original_join)


@pytest.mark.parametrize("first_fails", [False, True])
def test_completion_can_start_another_task(worker_window, qtbot, first_fails):
    calls = []

    def first():
        if first_fails:
            raise ValueError("retry this task")
        return 1

    def next_task(value, *duration):
        assert worker_window._worker is None and not worker_window.busy
        calls.append(value)
        worker_window.run_task("Second task", lambda: 2, lambda value, duration: calls.append(value))

    worker_window.run_task("First task", first, next_task, next_task)
    qtbot.waitUntil(lambda: len(calls) == 2, timeout=10000)
    assert calls[1] == 2
    assert worker_window._worker is None
    assert worker_window._on_success is None and worker_window._on_error is None
    assert worker_window.pool.activeThreadCount() == 0


def test_completed_workers_are_released(worker_window, qtbot, monkeypatch):
    workers, signals, calls = [], [], []

    class TrackedWorker(TaskWorker):
        def __init__(self, function, parent):
            super().__init__(function, parent)
            workers.append(weakref.ref(self))
            signals.append(weakref.ref(self.signals))

    def fails():
        raise ValueError("expected")

    def done(value, *duration):
        # Keeping exception tracebacks would intentionally retain their run frame.
        calls.append(str(value))

    monkeypatch.setattr(window_module, "TaskWorker", TrackedWorker)
    for index in range(20):
        worker_window.run_task("Release check", fails if index % 2 else lambda: 42, done, done)
        qtbot.waitUntil(lambda: not worker_window.busy, timeout=10000)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
    assert len(calls) == len(workers) == len(signals) == 20
    assert all(ref() is None for ref in workers)
    assert all(ref() is None for ref in signals)


def test_excel_import_with_collection_in_worker(worker_window, qtbot, tmp_path, monkeypatch):
    source = tmp_path / "Книга с пробелами.xlsx"
    with pd.ExcelWriter(source, engine="openpyxl") as writer:
        pd.DataFrame({"Name": ["Анна"]}).to_excel(writer, sheet_name="Первый", index=False)
        pd.DataFrame({"Name": ["Борис", "Иван"]}).to_excel(writer, sheet_name="Второй", index=False)
    original = source.read_bytes()
    threads = []
    gc_enabled = gc.isenabled()
    assert gc_enabled, "Exercise collection with automatic GC enabled"

    def inspect(path):
        threads.append(get_ident())
        gc.collect()
        return excel_sheets(path)

    monkeypatch.setattr(window_module, "excel_sheets", inspect)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("Второй", True))
    for _ in range(10):
        worker_window.load_path(source)
        qtbot.waitUntil(lambda: worker_window.manager.loaded and not worker_window.busy, timeout=10000)
        assert worker_window.manager.current.frame["Name"].tolist() == ["Борис", "Иван"]
        assert worker_window._worker is None and worker_window.pool.activeThreadCount() == 0
    assert len(threads) == 10
    assert all(thread != get_ident() for thread in threads)
    assert gc.isenabled() == gc_enabled
    assert source.read_bytes() == original
    moved = source.with_name("Переименованная книга.xlsx")
    source.rename(moved)  # On Windows this also checks that workbook file handles closed.


def test_close_rejected_until_worker_finishes(worker_window, qtbot, monkeypatch):
    release = Event()
    started = Event()
    calls = []
    notices = []

    def work():
        started.set()
        release.wait(5)
        return 42

    monkeypatch.setattr(QMessageBox, "information", lambda *args: notices.append(args[1]))
    worker_window.show()
    try:
        worker_window.run_task("Pending operation", work, lambda value, duration: calls.append(value))
        qtbot.waitUntil(started.is_set)
        assert not worker_window.close()
        assert worker_window.isVisible() and worker_window.busy
        assert notices == ["Operation in progress"] and calls == []
    finally:
        release.set()
    qtbot.waitUntil(lambda: bool(calls), timeout=10000)
    assert calls == [42]
    assert worker_window.close()
    assert worker_window.pool.activeThreadCount() == 0
