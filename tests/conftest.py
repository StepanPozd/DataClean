import os
from pathlib import Path

import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTEST_QT_API", "pyside6")
Path(__file__).resolve().parents[1].joinpath("test-output").mkdir(exist_ok=True)


@pytest.fixture
def finish_window(qtbot):
    def finish(widget):
        qtbot.waitUntil(lambda: not widget.busy and not widget._batch_active, timeout=15000)
        assert widget.pool.waitForDone(15000)
        widget.manager.mark_saved()

    return finish


@pytest.fixture
def dirty_frame():
    return pd.DataFrame(
        {
            "Name": ["  Анна  ", "Борис", "  Анна  ", None, "  ", "Елена"],
            "Score": [10.0, None, 10.0, None, None, 0.0],
            "City": ["Москва ", "Казань", "Москва ", None, "\t", "Омск"],
        }
    )
