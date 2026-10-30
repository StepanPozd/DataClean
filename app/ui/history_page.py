from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets import heading, label


class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 24)
        layout.setSpacing(21)
        layout.addLayout(
            heading(
                "A clear trail of every change",
                "Review imports, transformations and exports from this session.",
            )
        )
        self.summary = label("No activity yet. Import a file to get started.")
        layout.addWidget(self.summary)
        card = QFrame()
        card.setObjectName("tableCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(1, 10, 1, 10)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["TIME", "OPERATION", "ROWS", "DURATION", "STATUS", "RESULT"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(47)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        for index, width in enumerate([95, 170, 80, 95, 100, 330]):
            self.table.setColumnWidth(index, width)
        card_layout.addWidget(self.table)
        layout.addWidget(card, 1)
        layout.addWidget(
            label("Session history is kept in memory and clears when you close DataClean.", "small")
        )

    def refresh(self, entries):
        self.summary.setText(
            f"{len(entries):,} operations recorded in this session."
            if entries
            else "No activity yet. Import a file to get started."
        )
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(reversed(entries)):
            values = [
                entry.timestamp.strftime("%H:%M:%S"),
                entry.operation,
                f"{entry.rows:,}",
                f"{entry.duration:.2f} s",
                "Success" if entry.success else "Failed",
                entry.result,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if col == 4:
                    item.setForeground(QColor("#77d9b3" if entry.success else "#ed9a9f"))
                if col == 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
                self.table.setItem(row, col, item)
