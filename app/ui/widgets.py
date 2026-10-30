"""Reusable cards, buttons, and virtual data previews."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.models.dataframe_model import DataFrameModel
from app.ui.icons import icon


def label(text: str, name: str = "muted", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(
    text: str, symbol: str | None = None, primary: bool = False, name: str | None = None
) -> QPushButton:
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if symbol:
        widget.setIcon(icon(symbol, "#ffffff" if primary else "#a3b8dc"))
    if name or primary:
        widget.setObjectName(name or "primary")
    widget.setMinimumHeight(38)
    return widget


def heading(title: str, subtitle: str) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(7)
    layout.addWidget(label(title, "sectionTitle"))
    layout.addWidget(label(subtitle, wrap=True))
    return layout


class EmptyState(QWidget):
    import_requested = Signal()

    def __init__(self, title="A clean start for your data", subtitle=None, action=True, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)
        symbol = QLabel()
        symbol.setPixmap(icon("table", "#6f97ff", 52).pixmap(52, 52))
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(symbol)
        title_widget = label(title, "sectionTitle")
        title_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_widget)
        body = label(
            subtitle
            or "Import a spreadsheet to explore, clean and prepare your data.\n"
            "Your original file always stays safe.",
            wrap=True,
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(body)
        if action:
            import_button = button("Import your first file", "upload", primary=True)
            import_button.clicked.connect(self.import_requested)
            layout.addWidget(import_button, alignment=Qt.AlignmentFlag.AlignCenter)
            hint = label("CSV  /  XLSX    ·    Processed locally on your computer", "small")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)


class DataPreview(QFrame):
    import_requested = Signal()

    def __init__(
        self, title="Data preview", empty_title=None, empty_subtitle=None, allow_import=True, parent=None
    ):
        super().__init__(parent)
        self.setObjectName("tableCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(20, 16, 20, 16)
        header.addWidget(label(title, "cardTitle"))
        header.addStretch()
        self.badge = label("NO DATA", "badge")
        header.addWidget(self.badge)
        layout.addLayout(header)
        self.stack = QStackedWidget()
        self.empty = EmptyState(empty_title or "A clean start for your data", empty_subtitle, allow_import)
        self.empty.import_requested.connect(self.import_requested)
        self.stack.addWidget(self.empty)
        self.model = DataFrameModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(39)
        self.table.verticalHeader().setMinimumWidth(45)
        self.table.horizontalHeader().setDefaultSectionSize(162)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.horizontalHeader().setMinimumSectionSize(90)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.stack.addWidget(self.table)
        layout.addWidget(self.stack, 1)
        footer = QHBoxLayout()
        footer.setContentsMargins(19, 12, 19, 12)
        self.count = label("Waiting for a dataset", "small")
        footer.addWidget(self.count)
        footer.addStretch()
        footer.addWidget(label("Read-only preview", "small"))
        layout.addLayout(footer)

    def set_frame(self, frame, badge="DATASET"):
        self.model.set_frame(frame)
        self.stack.setCurrentIndex(0 if frame is None else 1)
        self.badge.setText(badge if frame is not None else "NO DATA")
        self.count.setText(
            f"{len(frame):,} rows  ·  {len(frame.columns):,} columns"
            if frame is not None
            else "Waiting for a dataset"
        )


class MetricCard(QFrame):
    def __init__(self, title, symbol, note, color="#7ba1ff"):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(135)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(19, 16, 19, 16)
        top = QHBoxLayout()
        top.addWidget(label(title, "metricLabel"))
        top.addStretch()
        glyph = QLabel()
        glyph.setPixmap(icon(symbol, color).pixmap(20, 20))
        top.addWidget(glyph)
        layout.addLayout(top)
        self.value = label("—", "metric")
        layout.addWidget(self.value)
        layout.addWidget(label(note, "small"))

    def set_value(self, value):
        self.value.setText(f"{value:,}" if value is not None else "—")
