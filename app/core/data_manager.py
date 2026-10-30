"""Session state. Frames are immutable by convention; transformations return new frames."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.data_processor import Statistics, statistics


@dataclass(frozen=True)
class Snapshot:
    frame: pd.DataFrame
    stats: Statistics
    memory_bytes: int = 0

    @classmethod
    def prepare(cls, frame: pd.DataFrame) -> "Snapshot":
        return cls(frame, statistics(frame), int(frame.memory_usage(deep=True).sum()))


class DataManager:
    MAX_UNDO = 10
    UNDO_BYTES = 256 * 1024 * 1024

    def __init__(self):
        self.current: Snapshot | None = None
        self.original: Snapshot | None = None
        self.undo_stack: list[Snapshot] = []
        self.saved: Snapshot | None = None
        self.source: Path | None = None
        self.name = "No file selected"
        self.protected_paths: set[str] = set()

    @property
    def loaded(self) -> bool:
        return self.current is not None

    @property
    def dirty(self) -> bool:
        return self.loaded and self.current is not self.saved

    def mark_saved(self):
        self.saved = self.current

    def load(self, snapshot: Snapshot, name: str, source: Path | None = None, *, saved=True):
        self.current = self.original = snapshot
        self.saved = snapshot if saved else None
        self.undo_stack.clear()
        self.name, self.source = name, source

    def apply(self, snapshot: Snapshot):
        if self.current is None:
            raise ValueError("Import a file first.")
        self.undo_stack.append(self.current)
        self.current = snapshot
        # Always retain at least the last action, including for a very large dataset.
        while len(self.undo_stack) > 1 and (
            len(self.undo_stack) > self.MAX_UNDO
            or sum(item.memory_bytes for item in self.undo_stack) > self.UNDO_BYTES
        ):
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            raise ValueError("There are no actions to undo.")
        self.current = self.undo_stack.pop()

    def reset(self):
        if self.original is None:
            raise ValueError("Import a file first.")
        if self.current is not self.original:
            self.apply(self.original)
