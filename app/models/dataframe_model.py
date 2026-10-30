"""A virtual, read-only view: values are formatted only when requested by Qt."""

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor


class DataFrameModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = pd.DataFrame()

    def set_frame(self, frame: pd.DataFrame | None):
        self.beginResetModel()
        self.frame = frame if frame is not None else pd.DataFrame()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.frame)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.frame.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (
            0 <= index.row() < self.rowCount() and 0 <= index.column() < self.columnCount()
        ):
            return None
        value = self.frame.iat[index.row(), index.column()]
        missing = bool(pd.isna(value))
        if role == Qt.ItemDataRole.DisplayRole:
            if missing:
                return "—"
            if isinstance(value, float):
                return format(value, ".12g")
            return str(value)
        if role == Qt.ItemDataRole.ToolTipRole:
            return "Missing value" if missing else str(value)
        if role == Qt.ItemDataRole.ForegroundRole and missing:
            return QColor("#d9ac68")
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return (
                str(self.frame.columns[section])
                if orientation == Qt.Orientation.Horizontal
                else str(section + 1)
            )
        if role == Qt.ItemDataRole.ToolTipRole and orientation == Qt.Orientation.Horizontal:
            return f"{self.frame.columns[section]} · {self.frame.dtypes.iloc[section]}"
        return None
