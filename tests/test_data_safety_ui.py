"""UI integration for explicit import modes and non-mutating export protection."""

import csv

import pandas as pd
import pytest
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from app.core.data_manager import Snapshot
from app.ui.dialogs import CsvOptionsDialog
from app.ui.main_window import CSV_CHECKED_FILTER, CSV_RAW_FILTER, MainWindow
from main import create_application


@pytest.fixture
def safety_window(qtbot, monkeypatch):
    create_application([])
    widget = MainWindow()
    qtbot.addWidget(widget)
    widget.errors = []
    widget.notices = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: widget.errors.append(args[2]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: widget.notices.append(args[2]))
    monkeypatch.setattr(widget, "confirm", lambda *args: True)
    widget.show()
    yield widget
    qtbot.waitUntil(lambda: not widget.busy and not widget._batch_active, timeout=15000)
    widget.manager.mark_saved()
    widget.close()


def test_import_dialog_explains_modes_and_defaults_to_preserving_text(qtbot):
    dialog = CsvOptionsDialog("Identifiers.csv")
    qtbot.addWidget(dialog)
    assert dialog.selected_mode() == "text"
    assert "NA, NULL" in dialog.mode_note.text()
    assert "Empty fields" in dialog.mode_note.text()
    dialog.interpretation.setCurrentIndex(1)
    assert dialog.selected_mode() == "auto"
    assert "round" in dialog.mode_note.text()


@pytest.mark.parametrize("mode", ["text", "auto"])
def test_import_dialog_choice_reaches_worker_and_history(safety_window, qtbot, tmp_path, monkeypatch, mode):
    path = tmp_path / "Identifiers.csv"
    path.write_text("ID,Token\n00123,NA\n00045,NULL\n", encoding="utf-8")
    before = path.read_bytes()

    def choose(dialog):
        dialog.interpretation.setCurrentIndex(0 if mode == "text" else 1)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(CsvOptionsDialog, "exec", choose)
    safety_window.load_path(path)
    qtbot.waitUntil(lambda: not safety_window.busy and safety_window.manager.loaded, timeout=10000)
    frame = safety_window.manager.current.frame
    if mode == "text":
        assert frame["ID"].tolist() == ["00123", "00045"]
        assert frame["Token"].tolist() == ["NA", "NULL"]
        assert "Text values" in safety_window.history.entries[-1].result
    else:
        assert frame["ID"].tolist() == [123, 45]
        assert frame["Token"].isna().all()
        assert "Automatic types" in safety_window.history.entries[-1].result
    assert path.read_bytes() == before


def test_encoding_retry_keeps_text_interpretation(safety_window, qtbot, tmp_path, monkeypatch):
    path = tmp_path / "Кодировка.csv"
    path.write_bytes("ID,Имя\n00123,Анна\n".encode("cp1251"))
    modes = []

    def retry(dialog):
        modes.append(dialog.selected_mode())
        return QDialog.DialogCode.Accepted  # Retry defaults to Windows-1251.

    monkeypatch.setattr(CsvOptionsDialog, "exec", retry)
    safety_window.load_path(path, encoding="utf-8", csv_mode="text")
    qtbot.waitUntil(lambda: not safety_window.busy and safety_window.manager.loaded, timeout=10000)
    assert modes == ["text"]
    assert safety_window.manager.current.frame.iat[0, 0] == "00123"


def test_merge_imports_preserve_identifiers_by_default(safety_window, qtbot, tmp_path, monkeypatch):
    paths = []
    for index, value in enumerate(["00123", "00045"]):
        path = tmp_path / f"{index}.csv"
        path.write_text(f"ID\n{value}\n", encoding="utf-8")
        paths.append(str(path))
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: (paths, ""))
    monkeypatch.setattr(CsvOptionsDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    safety_window.add_merge_files()
    qtbot.waitUntil(lambda: not safety_window.busy and not safety_window._batch_active, timeout=15000)
    assert all(loaded.csv_mode == "text" for loaded in safety_window.merge_page.files)
    safety_window.merge_files()
    qtbot.waitUntil(lambda: not safety_window.busy, timeout=10000)
    assert safety_window.merge_page.result.frame["ID"].tolist() == ["00123", "00045"]


def prepare_export(window, monkeypatch, path, frame, selected_filter):
    window.manager.load(Snapshot.prepare(frame), "Unsaved dataset", saved=False)
    window._refresh()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), selected_filter))


def test_xlsx_validation_failure_preserves_dirty_state_and_output(
    safety_window, qtbot, tmp_path, monkeypatch
):
    path = tmp_path / "existing.xlsx"
    path.write_bytes(b"previous output")
    prepare_export(
        safety_window, monkeypatch, path, pd.DataFrame({"Text": ["x" * 32768]}), "Excel workbook (*.xlsx)"
    )
    safety_window.export_current()
    qtbot.waitUntil(lambda: not safety_window.busy, timeout=10000)
    assert path.read_bytes() == b"previous output"
    assert "32,767" in safety_window.errors[-1]
    assert safety_window.manager.dirty
    assert not safety_window.notices
    assert not safety_window.history.entries[-1].success
    assert safety_window.import_button.isEnabled()
    assert safety_window.export_button.isEnabled()


def test_formula_checked_csv_failure_is_visible_and_values_unchanged(
    safety_window, qtbot, tmp_path, monkeypatch
):
    path = tmp_path / "blocked.csv"
    prepare_export(safety_window, monkeypatch, path, pd.DataFrame({"Text": ["=1+1"]}), CSV_CHECKED_FILTER)
    safety_window.export_current()
    qtbot.waitUntil(lambda: not safety_window.busy, timeout=10000)
    assert "formula" in safety_window.errors[-1]
    assert safety_window.manager.current.frame.iat[0, 0] == "=1+1"
    assert safety_window.manager.dirty
    assert not path.exists()
    assert not safety_window.notices


def test_raw_csv_requires_explicit_warning_and_does_not_escape_values(
    safety_window, qtbot, tmp_path, monkeypatch
):
    path = tmp_path / "raw.csv"
    prepare_export(
        safety_window, monkeypatch, path, pd.DataFrame({"Text": ["=1+1", "00123"]}), CSV_RAW_FILTER
    )
    confirmations = []
    monkeypatch.setattr(safety_window, "confirm", lambda *args: confirmations.append(args) or True)
    safety_window.export_current()
    qtbot.waitUntil(lambda: not safety_window.busy, timeout=10000)
    assert "disables formula checks" in confirmations[-1][1]
    assert "leading zeros" in confirmations[-1][1]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        assert list(csv.reader(handle)) == [["Text"], ["=1+1"], ["00123"]]
    assert "CSV raw" in safety_window.history.entries[-1].result
    assert not safety_window.manager.dirty


def test_declining_raw_csv_warning_creates_nothing_and_keeps_changes(safety_window, tmp_path, monkeypatch):
    path = tmp_path / "cancelled.csv"
    prepare_export(safety_window, monkeypatch, path, pd.DataFrame({"Text": ["=1+1"]}), CSV_RAW_FILTER)
    monkeypatch.setattr(safety_window, "confirm", lambda *args: False)
    safety_window.export_current()
    assert not safety_window.busy
    assert not path.exists()
    assert safety_window.manager.dirty
    assert not safety_window.history.entries
