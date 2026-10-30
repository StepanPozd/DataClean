import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from app.core.file_handler import read_file
from app.models.dataframe_model import DataFrameModel
from app.ui.dialogs import CsvOptionsDialog
from app.ui.main_window import MainWindow
from main import create_application


@pytest.fixture
def window(qtbot, monkeypatch, finish_window):
    create_application([])
    widget = MainWindow()
    qtbot.addWidget(widget, before_close_func=finish_window)
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[2]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args[2]))
    monkeypatch.setattr(widget, "confirm", lambda *args: True)
    widget.test_messages = messages
    widget.show()
    yield widget
    finish_window(widget)
    widget.close()


def load_csv(window, qtbot, tmp_path, dirty_frame):
    path = tmp_path / "Исходная таблица.csv"
    dirty_frame.to_csv(path, index=False, encoding="utf-8-sig")
    window.load_path(path, encoding="utf-8-sig")
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    return path


def test_start_empty_and_navigation(window, qtbot):
    assert window.isVisible()
    assert not window.export_button.isEnabled()
    assert not window.editor.undo_button.isEnabled()
    assert window.dashboard.preview.stack.currentIndex() == 0
    for index, nav in enumerate(window.nav_buttons):
        qtbot.mouseClick(nav, Qt.MouseButton.LeftButton)
        assert window.pages.currentIndex() == index


def test_import_clean_undo_reset_and_export(window, qtbot, monkeypatch, tmp_path, dirty_frame):
    source = load_csv(window, qtbot, tmp_path, dirty_frame)
    original = source.read_bytes()
    assert window.manager.current.stats.rows == 6
    assert window.dashboard.cards[0].value.text() == "6"
    assert window.export_button.isEnabled()
    window.navigate(1)
    qtbot.mouseClick(window.editor.actions["duplicates"], Qt.MouseButton.LeftButton)
    assert window.busy
    assert not window.import_button.isEnabled()
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert window.manager.current.stats.rows == 5
    assert window.editor.preview.model.rowCount() == 5
    qtbot.mouseClick(window.editor.undo_button, Qt.MouseButton.LeftButton)
    assert window.manager.current.stats.rows == 6
    window.clean("empty")
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert window.manager.current.stats.rows == 4
    window.clean("reset")
    assert window.manager.current.stats.rows == 6
    window.clean("trim")
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert window.manager.current.frame.iat[0, 0] == "Анна"
    target = tmp_path / "Результат.xlsx"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), "Excel workbook (*.xlsx)")
    )
    window.export_current()
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert target.exists()
    assert read_file(target).frame.iat[0, 0] == "Анна"
    assert source.read_bytes() == original
    assert not window.manager.dirty
    assert window.history_page.table.rowCount() >= 7


def test_excel_import_selects_chosen_sheet(window, qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    path = tmp_path / "Книга.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"Name": ["Анна"]}).to_excel(writer, sheet_name="Первый", index=False)
        pd.DataFrame({"Name": ["Борис", "Иван"]}).to_excel(writer, sheet_name="Второй", index=False)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("Второй", True))
    window.load_path(path)
    qtbot.waitUntil(lambda: window.manager.loaded and not window.busy, timeout=10000)
    assert window.manager.current.stats.rows == 2
    assert window.manager.current.frame.iat[0, 0] == "Борис"


def test_import_cancel_keeps_dataset(window, qtbot, tmp_path, dirty_frame, monkeypatch):
    load_csv(window, qtbot, tmp_path, dirty_frame)
    current = window.manager.current
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: ("", ""))
    window.import_file()
    assert window.manager.current is current


def test_invalid_file_is_reported_without_losing_work(window, qtbot, tmp_path, dirty_frame):
    load_csv(window, qtbot, tmp_path, dirty_frame)
    current = window.manager.current
    broken = tmp_path / "broken.xlsx"
    broken.write_bytes(b"broken")
    window.load_path(broken)
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert window.manager.current is current
    assert window.test_messages
    assert not window.history.entries[-1].success
    assert window.import_button.isEnabled()


def test_merge_batch_preview_use_and_export(window, qtbot, tmp_path, monkeypatch):
    paths = []
    for index in range(2):
        path = tmp_path / f"data {index}.csv"
        pd.DataFrame({"Name": [f"Name {index}"], "Value": [index]}).to_csv(path, index=False)
        paths.append(str(path))
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: (paths, ""))
    monkeypatch.setattr(CsvOptionsDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.add_merge_files()
    qtbot.waitUntil(lambda: not window._batch_active and not window.busy, timeout=15000)
    assert len(window.merge_page.files) == 2
    window.merge_files()
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert window.merge_page.result.stats.rows == 2
    assert window.merge_page.preview.model.rowCount() == 2
    assert window.export_button.isEnabled()
    target = tmp_path / "merged.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), "CSV UTF-8 BOM (*.csv)")
    )
    window.export_current()
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert len(read_file(target).frame) == 2
    window.use_merge()
    assert window.pages.currentIndex() == 1
    assert window.manager.current.stats.rows == 2
    assert window.manager.dirty
    window.navigate(2)
    window.merge_page.list.setCurrentRow(0)
    window.merge_page.remove_selected()
    assert window.merge_page.result is None
    assert not window.export_button.isEnabled()


def test_merge_mismatch_reenables_controls(window, qtbot, tmp_path):
    for index, column in enumerate(["A", "B"]):
        path = tmp_path / f"data{index}.csv"
        pd.DataFrame({column: [index]}).to_csv(path, index=False)
        window.merge_page.add_file(read_file(path))
    window.navigate(2)
    window.merge_files()
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert window.merge_page.result is None
    assert "Missing columns" in window.test_messages[-1]
    assert window.merge_page.merge_button.isEnabled()


def test_source_export_is_blocked_in_ui(window, qtbot, tmp_path, dirty_frame, monkeypatch):
    source = load_csv(window, qtbot, tmp_path, dirty_frame)
    before = source.read_bytes()
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(source), "CSV UTF-8 BOM (*.csv)")
    )
    window.export_current()
    assert not window.busy
    assert "protected" in window.test_messages[-1]
    assert source.read_bytes() == before


def test_fill_dialog_action_and_undo(window, qtbot, tmp_path, dirty_frame, monkeypatch):
    from app.ui.dialogs import FillDialog

    load_csv(window, qtbot, tmp_path, dirty_frame)
    monkeypatch.setattr(FillDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(FillDialog, "replacement", lambda self: "Нет данных")
    window.clean("fill")
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert window.manager.current.stats.missing == 0
    assert window.dashboard.cards[2].value.text() == "0"
    window.clean("undo")
    assert window.manager.current.stats.missing == 5


def test_declining_reset_preserves_working_state(window, qtbot, tmp_path, dirty_frame, monkeypatch):
    load_csv(window, qtbot, tmp_path, dirty_frame)
    window.clean("duplicates")
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    current = window.manager.current
    monkeypatch.setattr(window, "confirm", lambda *args: False)
    window.clean("reset")
    assert window.manager.current is current


def test_declining_overwrite_preserves_output(window, qtbot, tmp_path, dirty_frame, monkeypatch):
    load_csv(window, qtbot, tmp_path, dirty_frame)
    target = tmp_path / "existing.csv"
    target.write_bytes(b"existing output")
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), "CSV UTF-8 BOM (*.csv)")
    )
    monkeypatch.setattr(window, "confirm", lambda *args: False)
    window.export_current()
    assert target.read_bytes() == b"existing output"
    assert not window.busy


def test_model_virtual_values_and_missing_markers(qapp):
    model = DataFrameModel()
    model.set_frame(pd.DataFrame({"Имя": ["Анна", None], "Number": [1.5, 2.0]}))
    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.data(model.index(0, 0)) == "Анна"
    assert model.data(model.index(1, 0)) == "—"
    assert model.data(model.index(0, 1)) == "1.5"
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Имя"
    assert not model.flags(model.index(0, 0)) & Qt.ItemFlag.ItemIsEditable


def test_worker_callbacks_run_on_gui_thread(window, qtbot):
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QApplication

    threads = []
    called = []

    def work():
        threads.append(QThread.currentThread())
        return 42

    def done(value, duration):
        called.append((value, QThread.currentThread()))

    window.run_task("Thread check", work, done)
    qtbot.waitUntil(lambda: bool(called), timeout=10000)
    assert threads[0] != QApplication.instance().thread()
    assert called[0] == (42, QApplication.instance().thread())


def test_window_layout_fits_at_minimum_size(window, qtbot):
    window.resize(1080, 720)
    for index in range(4):
        window.navigate(index)
        qtbot.wait(10)
        assert window.width() == 1080
        page = window.pages.currentWidget()
        assert page.width() <= window.width() - 218
