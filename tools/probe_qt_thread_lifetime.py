"""Isolate pooled QThread wrapper lifetime, without DataClean, pytest-qt or Excel.

By default, only log wrapper metadata after the pool has joined. The explicit
--invoke-retired-method experiment intentionally crosses that lifetime boundary
and may crash this process. It is not an application regression test or CI gate.
"""

import argparse
import faulthandler
from threading import get_ident

import shiboken6
from PySide6.QtCore import QCoreApplication, QRunnable, QThread, QThreadPool, qVersion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoke-retired-method", action="store_true")
    args = parser.parse_args()
    faulthandler.enable()
    app = QCoreApplication([])
    pool = QThreadPool()
    seen = {}

    class CaptureThread(QRunnable):
        def __init__(self):
            super().__init__()
            self.setAutoDelete(False)

        def run(self):
            thread = QThread.currentThread()
            seen.update(wrapper=thread, identity=get_ident(), live_name=thread.objectName())

    worker = CaptureThread()
    pool.start(worker)
    if not pool.waitForDone(10000):
        raise TimeoutError("Pool did not terminate")
    shiboken6.delete(worker)
    print("Qt:", qVersion(), "pool joined; worker ID:", seen["identity"], "GUI ID:", get_ident(), flush=True)
    print("Name read inside live thread:", seen["live_name"], flush=True)
    print("Wrapper metadata isValid:", shiboken6.isValid(seen["wrapper"]), flush=True)
    if args.invoke_retired_method:
        print("Diagnostic: invoking objectName after pool termination", flush=True)
        try:
            print(seen["wrapper"].objectName(), flush=True)
        except RuntimeError as error:
            print(type(error).__name__, "invalid-wrapper guard rejected the call", flush=True)
    app.quit()


if __name__ == "__main__":
    main()
