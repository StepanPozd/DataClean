"""Run DataClean with Python 3.11+ (no server, browser, or cloud services)."""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from app import __version__
from app.ui.icons import application_icon
from app.ui.main_window import MainWindow
from app.ui.styles import STYLESHEET


def create_application(argv=None):
    application = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    application.setApplicationName("DataClean")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(application_icon())
    application.setOrganizationName("Stepan Pozdnyakov")
    application.setStyle("Fusion")
    application.setFont(QFont("Segoe UI", 10))
    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, "#191e28"),
        (QPalette.ColorRole.WindowText, "#d9e0ec"),
        (QPalette.ColorRole.Base, "#121720"),
        (QPalette.ColorRole.Text, "#d9e0ec"),
        (QPalette.ColorRole.Button, "#222a37"),
        (QPalette.ColorRole.ButtonText, "#d9e0ec"),
        (QPalette.ColorRole.Highlight, "#395c9f"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
    ]:
        palette.setColor(role, QColor(color))
    application.setPalette(palette)
    application.setStyleSheet(STYLESHEET)
    application.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    return application


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    application = create_application()
    window = MainWindow()
    window.show()
    if sys.platform == "win32":
        # Ask Windows to match its native title bar to the dark workspace.
        try:
            import ctypes

            enabled = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(window.winId()), 20, ctypes.byref(enabled), ctypes.sizeof(enabled)
            )
        except (AttributeError, OSError):
            pass
    if len(sys.argv) > 1:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: window.load_path(Path(sys.argv[1])))
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
