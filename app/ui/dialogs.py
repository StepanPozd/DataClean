from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from app.ui.widgets import label

ENCODINGS = {
    "Automatic detection": None,
    "UTF-8 / UTF-8 BOM": "utf-8-sig",
    "Windows-1251 (Cyrillic)": "cp1251",
    "Windows-1252 (Western Europe)": "cp1252",
    "UTF-16": "utf-16",
    "CP866 (DOS Cyrillic)": "cp866",
    "KOI8-R": "koi8-r",
    "ISO-8859-1": "iso-8859-1",
}


class CsvOptionsDialog(QDialog):
    def __init__(self, filename, parent=None, retry=False, csv_mode="text"):
        super().__init__(parent)
        self.setWindowTitle("CSV import settings")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(label(filename, "cardTitle", True))
        layout.addWidget(
            label(
                "Choose a CSV encoding. Use Windows-1251 for older Russian exports."
                if retry
                else "Detect the encoding automatically, or choose it manually.",
                wrap=True,
            )
        )
        self.encoding = QComboBox()
        self.encoding.addItems(ENCODINGS)
        if retry:
            self.encoding.setCurrentIndex(2)
        self.interpretation = QComboBox()
        self.interpretation.addItem("Text — preserve values (recommended)", "text")
        self.interpretation.addItem("Automatic type detection", "auto")
        self.interpretation.setCurrentIndex(0 if csv_mode == "text" else 1)
        form = QFormLayout()
        form.addRow("Encoding", self.encoding)
        form.addRow("Interpret values as", self.interpretation)
        layout.addLayout(form)
        self.mode_note = label("", wrap=True)
        self.interpretation.currentIndexChanged.connect(self._update_mode_note)
        self._update_mode_note()
        layout.addWidget(self.mode_note)
        layout.addWidget(
            label(
                "The first row must contain unique column names.\n"
                "Comma, semicolon, tab and pipe separators are detected automatically.",
                "small",
                True,
            )
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_encoding(self):
        return ENCODINGS[self.encoding.currentText()]

    def selected_mode(self):
        return self.interpretation.currentData()

    def _update_mode_note(self, *_):
        self.mode_note.setText(
            "Preserves leading zeros, NA, NULL, long IDs and decimal digits as text. "
            "Empty fields stay empty strings, not missing values. Remove Empty Rows still works."
            if self.selected_mode() == "text"
            else "Automatic detection can remove leading zeros and round numbers. NA, NULL and empty "
            "fields become missing values. Use Text for identifiers and precision-sensitive data."
        )


class FillDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fill missing values")
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(label("Give missing values a meaning", "cardTitle"))
        layout.addWidget(
            label(
                "Replace missing cells in every column. Empty strings and spaces are not missing values.",
                wrap=True,
            )
        )
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItems(["Text", "Number"])
        self.value = QLineEdit()
        self.value.setPlaceholderText("For example: Unknown or 0")
        form.addRow("Value type", self.kind)
        form.addRow("Replacement", self.value)
        layout.addLayout(form)
        layout.addWidget(
            label("Text in a numeric column creates a mixed-type column. Undo is available.", "small", True)
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.value.textChanged.connect(
            lambda text: buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(text))
        )
        layout.addWidget(buttons)

    def replacement(self):
        text = self.value.text()
        if self.kind.currentIndex() == 0:
            return text
        import math

        try:
            value = float(text)
        except ValueError as error:
            raise ValueError("Enter a valid number, for example 0 or 12.5.") from error
        if not math.isfinite(value):
            raise ValueError("Enter a finite number.")
        return int(value) if value.is_integer() else value
