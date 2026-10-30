"""Workers exchange plain Python data through queued Qt signals."""

from time import perf_counter
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    succeeded = Signal(object, float)
    failed = Signal(object, float)


class TaskWorker(QRunnable):
    def __init__(self, function: Callable):
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        started = perf_counter()
        try:
            result = self.function()
        except Exception as error:
            self.signals.failed.emit(error, perf_counter() - started)
        else:
            self.signals.succeeded.emit(result, perf_counter() - started)
