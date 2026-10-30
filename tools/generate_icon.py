"""Render the repository SVG and assemble a multi-resolution Windows icon."""

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]


def main():
    assets = ROOT / "assets"
    renderer = QSvgRenderer(str(assets / "icon.svg"))
    if not renderer.isValid():
        raise ValueError("Invalid application icon SVG")
    canvas = QImage(512, 512, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    if not canvas.save(str(assets / "icon.png")):
        raise OSError("Cannot save the PNG application icon")
    with Image.open(assets / "icon.png") as image:
        image.save(
            assets / "icon.ico", format="ICO", sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)]
        )
    with Image.open(assets / "icon.ico") as image:
        required = {(16, 16), (32, 32), (48, 48), (256, 256)}
        assert required <= image.ico.sizes()
    print("Generated assets/icon.png and icon.ico (16–256 px) from icon.svg")


if __name__ == "__main__":
    main()
