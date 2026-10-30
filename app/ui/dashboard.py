from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from app.ui.widgets import DataPreview, MetricCard, button, heading, label


class Dashboard(QWidget):
    import_requested = Signal()
    edit_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 24)
        layout.setSpacing(21)
        intro = QHBoxLayout()
        intro.addLayout(
            heading(
                "Your data, at a glance", "Understand your dataset. Turn messy records into reliable data."
            ),
            1,
        )
        self.edit_button = button("Open data editor", "arrow", name="ghost")
        self.edit_button.clicked.connect(self.edit_requested)
        self.edit_button.setEnabled(False)
        intro.addWidget(self.edit_button)
        layout.addLayout(intro)
        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        self.cards = [
            MetricCard("Total Rows", "rows", "Records in your dataset"),
            MetricCard("Total Columns", "columns", "Fields per record"),
            MetricCard("Missing Values", "missing", "Empty cells to review", "#e4b570"),
            MetricCard("Duplicate Rows", "copy", "Repeated records", "#a894ed"),
        ]
        for card in self.cards:
            metrics.addWidget(card, 1)
        layout.addLayout(metrics)
        self.preview = DataPreview()
        self.preview.import_requested.connect(self.import_requested)
        layout.addWidget(self.preview, 1)
        note = QFrame()
        note.setObjectName("notice")
        note_layout = QHBoxLayout(note)
        note_layout.setContentsMargins(16, 12, 16, 12)
        note_layout.setSpacing(14)
        note_layout.addWidget(label("A safer workspace", "cardTitle"))
        note_layout.addWidget(
            label("Changes stay in memory. Export a new file when you are ready.", wrap=True), 1
        )
        layout.addWidget(note)

    def refresh(self, snapshot, badge):
        self.preview.set_frame(snapshot.frame if snapshot else None, badge)
        values = (
            (snapshot.stats.rows, snapshot.stats.columns, snapshot.stats.missing, snapshot.stats.duplicates)
            if snapshot
            else (None,) * 4
        )
        for card, value in zip(self.cards, values):
            card.set_value(value)
        self.edit_button.setEnabled(snapshot is not None)
