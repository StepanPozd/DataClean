import os
from pathlib import Path

import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTEST_QT_API", "pyside6")
Path(__file__).resolve().parents[1].joinpath("test-output").mkdir(exist_ok=True)


@pytest.fixture
def dirty_frame():
    return pd.DataFrame(
        {
            "Name": ["  Анна  ", "Борис", "  Анна  ", None, "  ", "Елена"],
            "Score": [10.0, None, 10.0, None, None, 0.0],
            "City": ["Москва ", "Казань", "Москва ", None, "\t", "Омск"],
        }
    )
