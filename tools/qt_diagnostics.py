"""Opt-in pytest journal; no collection/deletion policy changes or GC suppression."""

import gc
import json
import os
import threading
import time
import weakref
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--qt-diagnostic-log", type=Path)


def pytest_configure(config):
    path = config.getoption("--qt-diagnostic-log")
    if path:
        config.pluginmanager.register(QtJournal(path), "dataclean-qt-journal")


class QtJournal:
    def __init__(self, path):
        from PySide6.QtCore import Qt

        from app.ui.main_window import MainWindow
        from app.workers.task_worker import TaskWorker

        root = Path(__file__).resolve().parents[1]
        path = path.resolve()
        if not path.is_relative_to(root / "test-output"):
            raise ValueError("Diagnostic journals must stay under test-output")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_APPEND, 0o600)
        self.main_thread = threading.get_ident()
        self.test = "session"
        self.refs = []
        self.patch = pytest.MonkeyPatch()
        self.record("journal-start", gc_enabled=gc.isenabled(), thresholds=gc.get_threshold())
        gc.callbacks.append(self.collection)

        original_init = TaskWorker.__init__
        original_run = TaskWorker.run
        original_window = MainWindow.__init__
        original_release = MainWindow._release_worker

        def watch(obj, role):
            key = id(obj)
            self.refs.append(
                weakref.ref(obj, lambda ref: self.record("wrapper-finalized", role=role, key=key))
            )

            def destroyed():
                self.record("qobject-destroyed", role=role, key=key)

            obj.destroyed.connect(destroyed, Qt.ConnectionType.DirectConnection)

        def init_worker(worker, function, signals_parent):
            original_init(worker, function, signals_parent)
            key = id(worker)
            self.refs.append(weakref.ref(worker, lambda ref: self.record("worker-finalized", key=key)))
            watch(worker.signals, "signals")
            self.record("worker-created", key=key, owner=id(signals_parent), auto_delete=worker.autoDelete())

        def run_worker(worker):
            self.record("worker-run-enter", key=id(worker))
            try:
                return original_run(worker)
            finally:
                self.record("worker-python-body-exit", key=id(worker))

        def init_window(window):
            original_window(window)
            watch(window, "window")
            self.record("window-created", key=id(window), pool=id(window.pool))

        def release_worker(window):
            self.record("gui-release-enter", window=id(window), active=window.pool.activeThreadCount())
            result = original_release(window)
            self.record("gui-release-exit", window=id(window), active=window.pool.activeThreadCount())
            return result

        self.patch.setattr(TaskWorker, "__init__", init_worker)
        self.patch.setattr(TaskWorker, "run", run_worker)
        self.patch.setattr(MainWindow, "__init__", init_window)
        self.patch.setattr(MainWindow, "_release_worker", release_worker)

    def record(self, event, **details):
        if self.fd is None:
            return
        item = {
            "event": event,
            "time_ns": time.perf_counter_ns(),
            "thread": threading.get_ident(),
            "native_thread": threading.get_native_id(),
            "gui_thread": threading.get_ident() == self.main_thread,
            "test": self.test,
            **details,
        }
        # One append per event; no buffered logger or cross-thread lock in GC hooks.
        os.write(self.fd, (json.dumps(item, ensure_ascii=True) + "\n").encode("utf-8"))

    def collection(self, phase, info):
        self.record("gc-" + phase, **info)

    def pytest_runtest_logstart(self, nodeid, location):
        self.test = nodeid
        self.record("test-start")

    def pytest_runtest_logreport(self, report):
        self.record("test-report", phase=report.when, outcome=report.outcome)

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_runtest_teardown(self, item):
        import shiboken6

        self.record("teardown-enter")
        result = yield
        valid = invalid = 0
        for ref in self.refs:
            obj = ref()
            if obj is not None:
                if shiboken6.isValid(obj):
                    valid += 1
                else:
                    invalid += 1
        self.record("teardown-exit", valid_wrappers=valid, invalid_wrappers=invalid)
        return result

    def pytest_sessionfinish(self, session, exitstatus):
        self.record("session-finish", exitstatus=int(exitstatus))
        gc.callbacks.remove(self.collection)
        self.patch.undo()
        os.close(self.fd)
        self.fd = None
