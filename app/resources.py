"""Read-only asset paths, independent of the process working directory."""

from pathlib import Path


def resource_path(relative: str) -> Path:
    # PyInstaller sets package __file__ inside onedir/_internal, mirroring this layout.
    return Path(__file__).resolve().parent.parent / relative
