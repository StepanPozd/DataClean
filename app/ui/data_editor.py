from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from app.ui.widgets import DataPreview, button, heading, label


class DataEditor(QWidget):
    operation_requested = Signal(str)
    import_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 24)
        layout.setSpacing(20)
        layout.addLayout(
            heading("Make every record count", "Clean your working copy with focused, reversible tools.")
        )
        tools = QGridLayout()
        tools.setSpacing(12)
        self.actions = {}
        definitions = [
            ("duplicates", "Remove Duplicates", "copy", "Keep the first occurrence of each identical row."),
            (
                "empty",
                "Remove Empty Rows",
                "trash",
                "Remove rows containing only missing or whitespace-only values.",
            ),
            ("trim", "Trim Whitespace", "clean", "Strip leading and trailing whitespace from text cells."),
            ("fill", "Fill Missing Values", "fill", "Replace missing cells with a text or numeric value."),
        ]
        for index, (key, title, symbol, tip) in enumerate(definitions):
            control = button(title, symbol)
            control.setMinimumHeight(49)
            control.setToolTip(tip)
            control.clicked.connect(
                lambda checked=False, operation=key: self.operation_requested.emit(operation)
            )
            self.actions[key] = control
            tools.addWidget(control, index // 2, index % 2)
        layout.addLayout(tools)
        bar = QHBoxLayout()
        self.summary = label("Import a dataset to enable cleaning tools.", wrap=True)
        bar.addWidget(self.summary, 1)
        self.undo_button = button("Undo Last Action", "undo")
        self.reset_button = button("Reset to Original", "reset", name="danger")
        self.undo_button.clicked.connect(lambda: self.operation_requested.emit("undo"))
        self.reset_button.clicked.connect(lambda: self.operation_requested.emit("reset"))
        bar.addWidget(self.undo_button)
        bar.addWidget(self.reset_button)
        layout.addLayout(bar)
        self.preview = DataPreview("Working dataset")
        self.preview.import_requested.connect(self.import_requested)
        layout.addWidget(self.preview, 1)
        layout.addWidget(
            label(
                "Missing values appear as —. Trimming keeps internal spaces; empty-row removal also recognizes whitespace.",
                "small",
                True,
            )
        )
        self.refresh(None, False, False, "DATASET")

    def refresh(self, snapshot, undo_available, changed, badge):
        loaded = snapshot is not None
        for action in self.actions.values():
            action.setEnabled(loaded)
        self.undo_button.setEnabled(loaded and undo_available)
        self.reset_button.setEnabled(loaded and changed)
        self.preview.set_frame(snapshot.frame if snapshot else None, badge)
        if loaded:
            stats = snapshot.stats
            self.summary.setText(
                f"{stats.rows:,} rows  ·  {stats.missing:,} missing values  ·  {stats.duplicates:,} duplicates"
            )
