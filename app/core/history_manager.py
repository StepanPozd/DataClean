"""In-memory audit trail for the current session."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HistoryEntry:
    timestamp: datetime
    operation: str
    rows: int
    result: str
    duration: float
    success: bool = True


class HistoryManager:
    def __init__(self):
        self.entries: list[HistoryEntry] = []

    def add(self, operation: str, rows: int, result: str, duration: float = 0, success: bool = True):
        self.entries.append(
            HistoryEntry(datetime.now().astimezone(), operation, rows, result, duration, success)
        )
