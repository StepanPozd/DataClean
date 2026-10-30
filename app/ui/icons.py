"""Small, consistent SVG line icons rendered locally by Qt."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from app.resources import resource_path

PATHS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 10v10M15 10v10"/>',
    "merge": '<path d="M5 3v4c0 4 14 4 14 9v5M19 3v4c0 4-14 4-14 9v5M2 18l3 3 3-3M16 18l3 3 3-3"/>',
    "history": '<path d="M3 10a9 9 0 1 1 1 7M3 4v6h6M12 7v5l3 2"/>',
    "upload": '<path d="M12 16V3M7 8l5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
    "download": '<path d="M12 3v13M7 11l5 5 5-5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
    "rows": '<path d="M8 5h13M8 12h13M8 19h13M3 5h.1M3 12h.1M3 19h.1"/>',
    "columns": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16"/>',
    "missing": '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/>',
    "copy": '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    "clean": '<path d="M14 3l7 7M17.5 6.5L7 17M3 14l7 7 5-5-7-7zM12 19l2 2M4 4v4M2 6h4"/>',
    "fill": '<path d="M4 4h16v16H4zM8 12h8M12 8v8"/>',
    "undo": '<path d="M8 5L3 10l5 5M3 10h11a6 6 0 0 1 0 12"/>',
    "reset": '<path d="M4 9a8 8 0 1 1 0 6M4 3v6h6"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h6"/>',
    "arrow": '<path d="M4 12h16M14 6l6 6-6 6"/>',
    "check": '<path d="M5 12l4 4L19 6"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
    "plus": '<path d="M12 4v16M4 12h16"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    "logo": '<rect x="3" y="3" width="7" height="7" rx="1" fill="currentColor"/><rect x="14" y="3" width="7" height="7" rx="1" fill="currentColor"/><rect x="3" y="14" width="7" height="7" rx="1" fill="currentColor"/><path d="M14 17.5l2.5 2.5L22 14" stroke-width="2.5"/>',
}


def application_icon() -> QIcon:
    return QIcon(str(resource_path("assets/icon.ico")))


def icon(name: str, color: str = "#a3afc2", size: int = 20) -> QIcon:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" color="{color}" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
        f"{PATHS[name]}</svg>"
    )
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
