from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QListWidget, QSplitter, QVBoxLayout, QWidget

from app.ui.widgets import DataPreview, button, heading, label


class MergePage(QWidget):
    state_changed = Signal()
    add_requested = Signal()
    merge_requested = Signal()
    use_requested = Signal()
    export_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.files = []
        self.result = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 24)
        layout.setSpacing(21)
        layout.addLayout(
            heading(
                "Bring your files together",
                "Combine records from CSV and Excel files with matching column names.",
            )
        )
        splitter = QSplitter()
        left = QFrame()
        left.setObjectName("card")
        left.setMinimumWidth(265)
        left.setMaximumWidth(360)
        controls = QVBoxLayout(left)
        controls.setContentsMargins(17, 19, 17, 19)
        controls.setSpacing(14)
        controls.addWidget(label("Source files", "cardTitle"))
        self.add_button = button("Add files", "plus")
        self.add_button.clicked.connect(self.add_requested)
        controls.addWidget(self.add_button)
        self.list = QListWidget()
        controls.addWidget(self.list, 1)
        self.remove_button = button("Remove selected", "trash", name="ghost")
        self.remove_button.clicked.connect(self.remove_selected)
        controls.addWidget(self.remove_button)
        self.compatibility = label("Add at least two files.\nColumn order may differ.", wrap=True)
        controls.addWidget(self.compatibility)
        self.merge_button = button("Merge files", "merge", primary=True)
        self.merge_button.clicked.connect(self.merge_requested)
        controls.addWidget(self.merge_button)
        splitter.addWidget(left)
        self.preview = DataPreview(
            "Merged result",
            "One table. More possibilities.",
            "Add files on the left, then merge them to preview the result.",
            False,
        )
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 660])
        layout.addWidget(splitter, 1)
        footer = QHBoxLayout()
        footer.addWidget(label("Original files stay untouched.", "small"), 1)
        self.use_button = button("Use in data editor", "arrow")
        self.export_button = button("Export result", "download", primary=True)
        self.use_button.clicked.connect(self.use_requested)
        self.export_button.clicked.connect(self.export_requested)
        footer.addWidget(self.use_button)
        footer.addWidget(self.export_button)
        layout.addLayout(footer)
        self.list.currentRowChanged.connect(self.update_controls)
        self.update_controls()

    def invalidate_result(self):
        self.result = None
        self.preview.set_frame(None)

    def add_file(self, loaded):
        self.files.append(loaded)
        suffix = f" · {loaded.sheet}" if loaded.sheet else f" · {loaded.encoding}"
        if loaded.csv_mode:
            suffix += " · " + ("text" if loaded.csv_mode == "text" else "auto")
        self.list.addItem(f"{loaded.path.name}\n{len(loaded.frame):,} rows{suffix}")
        item = self.list.item(self.list.count() - 1)
        item.setToolTip(str(loaded.path))
        self.invalidate_result()
        self.update_controls()

    def remove_selected(self):
        row = self.list.currentRow()
        if row >= 0:
            self.files.pop(row)
            self.list.takeItem(row)
            self.invalidate_result()
            self.update_controls()

    def set_result(self, snapshot):
        self.result = snapshot
        self.preview.set_frame(snapshot.frame, "MERGED")
        self.update_controls()

    def update_controls(self, *_):
        self.remove_button.setEnabled(self.list.currentRow() >= 0)
        compatible = len(self.files) >= 2 and all(
            set(file.frame.columns) == set(self.files[0].frame.columns) for file in self.files[1:]
        )
        if len(self.files) >= 2:
            self.compatibility.setText(
                f"{len(self.files)} files · "
                + (
                    "columns match. Ready to merge."
                    if compatible
                    else "columns differ. Merge will explain which columns need attention."
                )
            )
        else:
            self.compatibility.setText("Add at least two files.\nColumn order may differ.")
        self.merge_button.setEnabled(len(self.files) >= 2)
        self.use_button.setEnabled(self.result is not None)
        self.export_button.setEnabled(self.result is not None)
        self.state_changed.emit()
