"""Application orchestration. All widget and model changes stay on the GUI thread."""

import logging
from pathlib import Path
from time import perf_counter
from typing import Callable

from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import delete

from app import __version__
from app.core import data_processor as processor
from app.core.data_manager import DataManager, Snapshot
from app.core.file_handler import (
    EncodingReadError,
    canonical,
    excel_sheets,
    export_file,
    read_file,
)
from app.core.history_manager import HistoryManager
from app.ui.dashboard import Dashboard
from app.ui.data_editor import DataEditor
from app.ui.dialogs import CsvOptionsDialog, FillDialog
from app.ui.history_page import HistoryPage
from app.ui.icons import application_icon, icon
from app.ui.merge_page import MergePage
from app.ui.widgets import button, label
from app.workers.task_worker import TaskWorker

LOGGER = logging.getLogger(__name__)
FILE_FILTER = "Tabular data (*.csv *.xlsx);;CSV files (*.csv);;Excel workbooks (*.xlsx)"
CSV_CHECKED_FILTER = "CSV formula-checked (*.csv)"
CSV_RAW_FILTER = "CSV exact values (unprotected) (*.csv)"
PAGES = [("Dashboard", "grid"), ("Data Editor", "table"), ("Merge Files", "merge"), ("History", "history")]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = DataManager()
        self.history = HistoryManager()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.busy = False
        self._worker = None
        self._on_success = None
        self._on_error = None
        self._task_name = ""
        self._batch_paths = []
        self._batch_active = False
        self._batch_new_count = 0
        self.setWindowTitle("DataClean — Spreadsheet workspace")
        self.setWindowIcon(application_icon())
        self.resize(1340, 850)
        self.setMinimumSize(1080, 720)
        self._build_ui()
        self._connect_ui()
        self._refresh()
        self._shortcuts = []
        for sequence, callback in [
            ("Ctrl+O", self.import_file),
            ("Ctrl+E", self.export_current),
            ("Ctrl+Z", lambda: self.clean("undo")),
        ]:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)
        for index in range(4):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda i=index: self.navigate(i))
            self._shortcuts.append(shortcut)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(218)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 29, 16, 20)
        side.setSpacing(8)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icon("logo", "#739bff", 29).pixmap(29, 29))
        brand.addWidget(logo)
        brand.addWidget(label("DataClean", "brand"))
        brand.addStretch()
        side.addLayout(brand)
        side.addWidget(label("    SPREADSHEET WORKSPACE", "brandSub"))
        side.addSpacing(38)
        side.addWidget(label("  WORKSPACE", "eyebrow"))
        side.addSpacing(8)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = []
        for index, (title, symbol) in enumerate(PAGES):
            nav = button(title, symbol, name="nav")
            nav.setCheckable(True)
            nav.setIconSize(QSize(20, 20))
            self.nav_group.addButton(nav, index)
            self.nav_buttons.append(nav)
            side.addWidget(nav)
        self.nav_buttons[0].setChecked(True)
        side.addStretch()
        note = QFrame()
        note.setObjectName("sideNote")
        note_layout = QVBoxLayout(note)
        note_layout.setContentsMargins(14, 16, 14, 16)
        note_layout.setSpacing(8)
        shield = QLabel()
        shield.setPixmap(icon("shield", "#79a4ff", 24).pixmap(24, 24))
        note_layout.addWidget(shield)
        note_layout.addWidget(label("Your files. Your control.", "cardTitle", True))
        note_layout.addWidget(
            label("All processing happens locally. Original files stay safe.", "small", True)
        )
        side.addWidget(note)
        side.addSpacing(13)
        side.addWidget(label(f"DataClean  /  v{__version__}", "small"))
        layout.addWidget(sidebar)
        workspace = QVBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(0)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setMinimumHeight(100)
        top = QHBoxLayout(topbar)
        top.setContentsMargins(30, 19, 30, 19)
        title = QVBoxLayout()
        title.setSpacing(5)
        self.page_title = label("Dashboard", "pageTitle")
        self.file_title = label("No file selected", "small")
        self.file_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title.addWidget(self.page_title)
        title.addWidget(self.file_title)
        top.addLayout(title, 1)
        top.setSpacing(12)
        self.import_button = button("Import File", "upload")
        self.import_button.setFixedWidth(132)
        self.import_button.setToolTip("Import a CSV or XLSX file · Ctrl+O")
        self.export_button = button("Export", "download", primary=True)
        self.export_button.setFixedWidth(112)
        self.export_button.setToolTip("Export the active dataset · Ctrl+E")
        top.addWidget(self.import_button)
        top.addWidget(self.export_button)
        workspace.addWidget(topbar)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        workspace.addWidget(self.progress)
        self.pages = QStackedWidget()
        self.dashboard = Dashboard()
        self.editor = DataEditor()
        self.merge_page = MergePage()
        self.history_page = HistoryPage()
        for page in [self.dashboard, self.editor, self.merge_page, self.history_page]:
            self.pages.addWidget(page)
        workspace.addWidget(self.pages, 1)
        layout.addLayout(workspace, 1)
        self.status_label = label("Ready to import a dataset", "small")
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(label("●  Local processing", "statusDot"))
        self.statusBar().setSizeGripEnabled(True)

    def _connect_ui(self):
        self.nav_group.idClicked.connect(self.navigate)
        self.import_button.clicked.connect(self.import_file)
        self.export_button.clicked.connect(self.export_current)
        self.dashboard.import_requested.connect(self.import_file)
        self.dashboard.edit_requested.connect(lambda: self.navigate(1))
        self.editor.import_requested.connect(self.import_file)
        self.editor.operation_requested.connect(self.clean)
        self.merge_page.add_requested.connect(self.add_merge_files)
        self.merge_page.merge_requested.connect(self.merge_files)
        self.merge_page.use_requested.connect(self.use_merge)
        self.merge_page.export_requested.connect(lambda: self.export_current(merge=True))
        self.merge_page.state_changed.connect(self._refresh_header)

    @Slot(int)
    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        self.page_title.setText(PAGES[index][0])
        self._refresh_header()

    def _refresh_header(self):
        merge_active = self.pages.currentIndex() == 2
        name = f"{len(self.merge_page.files)} source files selected" if merge_active else self.manager.name
        self.file_title.setText(("●  " if self.manager.dirty and not merge_active else "") + name)
        self.file_title.setToolTip(str(self.manager.source or name))
        available = self.merge_page.result is not None if merge_active else self.manager.loaded
        self.export_button.setEnabled(available and not self.busy and not self._batch_active)
        self.import_button.setEnabled(not self.busy and not self._batch_active)
        self.setWindowTitle(f"DataClean — {self.manager.name}" + (" *" if self.manager.dirty else ""))

    def _refresh(self):
        badge = self.manager.source.suffix[1:].upper() if self.manager.source else "DATASET"
        self.dashboard.refresh(self.manager.current, badge)
        self.editor.refresh(
            self.manager.current,
            bool(self.manager.undo_stack),
            self.manager.current is not self.manager.original,
            badge,
        )
        self.history_page.refresh(self.history.entries)
        self.merge_page.update_controls()
        self._refresh_header()

    def _set_busy(self, busy, message=""):
        self.busy = busy
        self.pages.setEnabled(not busy and not self._batch_active)
        self.progress.setVisible(busy)
        if message:
            self.status_label.setText(message)
        self._refresh_header()

    def run_task(self, name: str, function: Callable, success: Callable, error=None):
        if self.busy:
            return
        self._task_name, self._on_success, self._on_error = name, success, error
        self._set_busy(True, name + "…")
        worker = TaskWorker(function, self)
        self._worker = worker
        worker.signals.succeeded.connect(self._task_succeeded, Qt.ConnectionType.QueuedConnection)
        worker.signals.failed.connect(self._task_failed, Qt.ConnectionType.QueuedConnection)
        self.pool.start(worker)

    def _release_worker(self):
        # A queued result can reach the GUI before emit()/run() returns. Join
        # before dropping references, enabling another task or closing the window.
        self.pool.waitForDone()
        worker = self._worker
        self._worker = None
        self._on_success = self._on_error = None
        worker.function = None
        worker.signals.deleteLater()
        # PySide also retains non-auto-deleting runnables as pool children.
        # Explicitly dispose the C++ runnable here, after the pool has joined.
        delete(worker)

    @Slot(object, float)
    def _task_succeeded(self, result, duration):
        callback = self._on_success
        self._release_worker()
        self._set_busy(False)
        try:
            callback(result, duration)
        except Exception as error:
            LOGGER.exception("Completion callback failed")
            self.show_error(str(error))

    @Slot(object, float)
    def _task_failed(self, error, duration):
        callback = self._on_error
        operation = self._task_name
        self._release_worker()
        self._set_busy(False)
        self.history.add(operation, 0, str(error), duration, False)
        self.history_page.refresh(self.history.entries)
        self.status_label.setText(operation + " failed")
        if callback:
            callback(error)
        else:
            self.show_error(str(error))

    def show_error(self, message):
        QMessageBox.warning(self, "DataClean · Please check", message)

    def confirm(self, title, message):
        return (
            QMessageBox.question(
                self,
                title,
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    def _can_replace(self):
        return not self.manager.dirty or self.confirm(
            "Replace working dataset?",
            "Your working dataset has unexported changes.\n"
            "Replace it? Export first if you want to keep those changes.",
        )

    @Slot()
    def import_file(self):
        if self.busy or self._batch_active:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Import a dataset", "", FILE_FILTER)
        if path and self._can_replace():
            self.load_path(Path(path))

    def load_path(self, path: Path, *, encoding=None, sheet=None, csv_mode="auto"):
        """Public import entry point; also useful for CLI and integration tests."""
        self._request_read(Path(path), self._import_loaded, encoding=encoding, sheet=sheet, csv_mode=csv_mode)

    def _request_read(
        self, path, callback, *, encoding=None, sheet=None, csv_options=True, cancelled=None, csv_mode="auto"
    ):
        def cancel():
            if cancelled:
                cancelled()

        def read(selected_sheet=None, selected_encoding=None, selected_mode=csv_mode):
            def failed(error):
                if isinstance(error, EncodingReadError):
                    self.show_error(str(error))
                    dialog = CsvOptionsDialog(path.name, self, retry=True, csv_mode=selected_mode)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        read(selected_sheet, dialog.selected_encoding(), dialog.selected_mode())
                    else:
                        cancel()
                else:
                    self.show_error(str(error))
                    cancel()

            def prepare():
                loaded = read_file(
                    path, encoding=selected_encoding, sheet=selected_sheet, csv_mode=selected_mode
                )
                return loaded, Snapshot.prepare(loaded.frame)

            self.run_task("Import " + path.name, prepare, callback, failed)

        if path.suffix.lower() == ".xlsx" and sheet is None:

            def inspected(sheets, duration):
                if len(sheets) > 1:
                    selected, ok = QInputDialog.getItem(self, "Select worksheet", path.name, sheets, 0, False)
                    if not ok:
                        cancel()
                        return
                else:
                    selected = sheets[0]
                read(selected, None)

            def inspection_failed(error):
                self.show_error(str(error))
                cancel()

            self.run_task("Read workbook sheets", lambda: excel_sheets(path), inspected, inspection_failed)
        elif path.suffix.lower() == ".csv" and encoding is None and csv_options:
            dialog = CsvOptionsDialog(path.name, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                read(None, dialog.selected_encoding(), dialog.selected_mode())
            else:
                cancel()
        else:
            read(sheet, encoding)

    def _import_loaded(self, result, duration):
        loaded, snapshot = result
        self.manager.protected_paths.add(canonical(loaded.path))
        self.manager.load(snapshot, loaded.path.name, loaded.path)
        note = loaded.sheet or loaded.encoding or ""
        if loaded.csv_mode:
            note += " · " + ("Text values" if loaded.csv_mode == "text" else "Automatic types")
        self.history.add("Import file", snapshot.stats.rows, f"{loaded.path.name} · {note}", duration)
        self._refresh()
        self.status_label.setText(f"Imported {snapshot.stats.rows:,} rows · {note}")

    @Slot(str)
    def clean(self, operation):
        if self.busy or self._batch_active or not self.manager.loaded:
            return
        if operation == "undo":
            if not self.manager.undo_stack:
                return
            started = perf_counter()
            self.manager.undo()
            self.history.add(
                "Undo last action",
                len(self.manager.current.frame),
                "Previous working state restored.",
                perf_counter() - started,
            )
            self._refresh()
            self.status_label.setText("Previous working state restored")
            return
        if operation == "reset":
            if self.manager.current is self.manager.original:
                return
            if self.confirm(
                "Reset to original?",
                "Restore the dataset as it was when imported?\n"
                "You can undo this reset. Source files will remain unchanged.",
            ):
                self.manager.reset()
                self.history.add(
                    "Reset to original", len(self.manager.current.frame), "Original dataset restored."
                )
                self._refresh()
                self.status_label.setText("Original dataset restored")
            return
        transforms = {
            "duplicates": ("Remove duplicates", processor.remove_duplicates),
            "empty": ("Remove empty rows", processor.remove_empty_rows),
            "trim": ("Trim whitespace", processor.trim_whitespace),
        }
        if operation == "fill":
            dialog = FillDialog(self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                replacement = dialog.replacement()
            except ValueError as error:
                self.show_error(str(error))
                return
            name, transform = "Fill missing values", lambda frame: processor.fill_missing(frame, replacement)
        else:
            name, transform = transforms[operation]
        snapshot = self.manager.current

        def prepare():
            result = transform(snapshot.frame)
            return result, Snapshot.prepare(result.frame)

        def done(result, duration):
            processed, updated = result
            if processed.affected:
                self.manager.apply(updated)
            self.history.add(name, processed.affected, processed.detail, duration)
            self._refresh()
            self.status_label.setText(processed.detail)

        self.run_task(name, prepare, done)

    @Slot()
    def add_merge_files(self):
        if self.busy or self._batch_active:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files to combine", "", FILE_FILTER)
        if not paths:
            return
        existing = {canonical(file.path) for file in self.merge_page.files}
        self._batch_paths = [Path(path) for path in dict.fromkeys(paths) if canonical(path) not in existing]
        if not self._batch_paths:
            self.status_label.setText("Those files have already been added")
            return
        self.navigate(2)
        self._batch_active = True
        self._batch_new_count = 0
        self.pages.setEnabled(False)
        self._refresh_header()
        self._next_merge_file()

    def _next_merge_file(self):
        if not self._batch_paths:
            self._batch_active = False
            self.pages.setEnabled(True)
            self._refresh_header()
            self.status_label.setText(f"Added {self._batch_new_count} source files")
            return
        path = self._batch_paths.pop(0)

        def added(result, duration):
            loaded, snapshot = result
            self.manager.protected_paths.add(canonical(loaded.path))
            self.merge_page.add_file(loaded)
            self._batch_new_count += 1
            self.history.add("Add merge source", snapshot.stats.rows, loaded.path.name, duration)
            self.history_page.refresh(self.history.entries)
            QTimer.singleShot(0, self._next_merge_file)

        self._request_read(path, added, cancelled=lambda: QTimer.singleShot(0, self._next_merge_file))

    @Slot()
    def merge_files(self):
        if self.busy or self._batch_active or len(self.merge_page.files) < 2:
            return
        files = list(self.merge_page.files)

        def prepare():
            return Snapshot.prepare(
                processor.merge_frames([item.frame for item in files], [item.path.name for item in files])
            )

        def merged(snapshot, duration):
            self.merge_page.set_result(snapshot)
            self.history.add("Merge files", snapshot.stats.rows, f"Combined {len(files)} files.", duration)
            self.history_page.refresh(self.history.entries)
            self._refresh_header()
            self.status_label.setText(f"Merged {len(files)} files · {snapshot.stats.rows:,} rows")

        self.run_task("Merge files", prepare, merged)

    @Slot()
    def use_merge(self):
        if self.busy or self._batch_active or self.merge_page.result is None or not self._can_replace():
            return
        self.manager.load(self.merge_page.result, "Merged dataset", saved=False)
        self.history.add(
            "Open merged dataset", self.manager.current.stats.rows, "Merged result opened in editor."
        )
        self._refresh()
        self.navigate(1)
        self.status_label.setText("Merged dataset ready for cleaning")

    def export_current(self, checked=False, *, merge=None):
        if self.busy or self._batch_active:
            return
        use_merge = self.pages.currentIndex() == 2 if merge is None else merge
        snapshot = self.merge_page.result if use_merge else self.manager.current
        if snapshot is None:
            return
        stem = "merged_data" if use_merge else Path(self.manager.name).stem + "_cleaned"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export dataset — XLSX preserves text types in spreadsheets",
            stem + ".xlsx",
            f"Excel workbook (*.xlsx);;{CSV_CHECKED_FILTER};;{CSV_RAW_FILTER}",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".csv" if "*.csv" in selected_filter else ".xlsx")
        if canonical(target) in self.manager.protected_paths:
            self.show_error("Source files are protected. Choose a new filename for your export.")
            return
        overwrite = target.exists()
        if overwrite and not self.confirm(
            "Overwrite exported file?", f"{target.name} already exists.\nReplace this file?"
        ):
            return
        csv_mode = "raw" if selected_filter == CSV_RAW_FILTER else "spreadsheet"
        if target.suffix.lower() == ".csv":
            notice = (
                "CSV exact values disables formula checks. Values beginning with =, +, -, @ or "
                "control characters can be interpreted as formulas. Do not open this file directly "
                "in a spreadsheet. Use XLSX for literal text.\n\n"
                if csv_mode == "raw"
                else "Formula-checked CSV blocks potentially formula-like values; it does not add "
                "apostrophes, tabs or other prefixes.\n\n"
            )
            notice += (
                "CSV cannot store cell types. A spreadsheet can remove leading zeros, round long "
                "IDs or reinterpret dates. Use XLSX, or import all CSV columns as Text. "
                "Export CSV with unchanged values?"
            )
            if not self.confirm("CSV export settings", notice):
                return

        def exported(destination, duration):
            if not use_merge:
                self.manager.mark_saved()
            detail = str(destination)
            if destination.suffix.lower() == ".csv":
                detail += f" · CSV {csv_mode} · values unchanged"
            self.history.add("Export file", snapshot.stats.rows, detail, duration)
            self._refresh()
            self.status_label.setText(f"Export complete · {destination.name}")
            QMessageBox.information(
                self, "Export complete", f"Saved {snapshot.stats.rows:,} rows to:\n{destination}"
            )

        protected = self.manager.protected_paths.copy()
        self.run_task(
            "Export file",
            lambda: export_file(
                snapshot.frame, target, protected_paths=protected, overwrite=overwrite, csv_mode=csv_mode
            ),
            exported,
        )

    def closeEvent(self, event):
        if self.busy or self._batch_active:
            QMessageBox.information(
                self,
                "Operation in progress",
                "Please wait for the current operation to finish before closing DataClean.",
            )
            event.ignore()
        elif self.manager.dirty and not self.confirm(
            "Close DataClean?", "Your dataset has unexported changes.\nClose and discard these changes?"
        ):
            event.ignore()
        else:
            self.pool.waitForDone()
            event.accept()
