"""Pure transformations: never mutate an input DataFrame."""

from dataclasses import dataclass
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype, is_object_dtype, is_string_dtype


@dataclass(frozen=True)
class Statistics:
    rows: int
    columns: int
    missing: int
    duplicates: int


@dataclass(frozen=True)
class ProcessResult:
    frame: pd.DataFrame
    affected: int
    detail: str


def statistics(frame: pd.DataFrame) -> Statistics:
    return Statistics(
        len(frame), len(frame.columns), int(frame.isna().sum().sum()), int(frame.duplicated().sum())
    )


def remove_duplicates(frame: pd.DataFrame) -> ProcessResult:
    result = frame.drop_duplicates().reset_index(drop=True)
    count = len(frame) - len(result)
    return ProcessResult(result, count, f"Removed {count:,} duplicate rows.")


def remove_empty_rows(frame: pd.DataFrame) -> ProcessResult:
    # Whitespace-only cells are empty too; zero and False remain valid values.
    empty = frame.isna() | frame.apply(
        lambda col: col.map(lambda value: isinstance(value, str) and not value.strip())
    )
    mask = empty.all(axis=1)
    count = int(mask.sum())
    return ProcessResult(frame.loc[~mask].reset_index(drop=True), count, f"Removed {count:,} empty rows.")


def trim_whitespace(frame: pd.DataFrame) -> ProcessResult:
    result = frame.copy(deep=True)
    changed_rows = pd.Series(False, index=frame.index)
    changed_cells = 0
    for column in frame.columns:
        mask = frame[column].map(lambda value: isinstance(value, str) and value != value.strip())
        changed_rows |= mask
        changed_cells += int(mask.sum())
        if mask.any():
            result[column] = frame[column].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )
    return ProcessResult(
        result,
        int(changed_rows.sum()),
        f"Trimmed {changed_cells:,} cells in {int(changed_rows.sum()):,} rows.",
    )


def fill_missing(frame: pd.DataFrame, value: Any) -> ProcessResult:
    if value is None or (isinstance(value, str) and not value):
        raise ValueError("Enter a non-empty replacement value.")
    missing = frame.isna()
    result = frame.copy(deep=True)
    for column in frame.columns:
        mask = missing[column]
        if mask.any():
            dtype = result[column].dtype
            compatible = (
                is_object_dtype(dtype)
                or (is_string_dtype(dtype) and isinstance(value, str))
                or (
                    is_numeric_dtype(dtype)
                    and not is_bool_dtype(dtype)
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                )
                or (is_bool_dtype(dtype) and isinstance(value, bool))
            )
            if not compatible:
                result[column] = result[column].astype(object)
            try:
                result[column] = result[column].where(~mask, value)
            except (TypeError, ValueError):
                # Text replacements in numeric columns intentionally produce mixed data.
                result[column] = result[column].astype(object).where(~mask, value)
    count = int(missing.sum().sum())
    return ProcessResult(result, int(missing.any(axis=1).sum()), f"Filled {count:,} missing values.")


def merge_frames(frames: list[pd.DataFrame], names: list[str] | None = None) -> pd.DataFrame:
    if len(frames) < 2:
        raise ValueError("Select at least two files to merge.")
    columns = list(frames[0].columns)
    expected = set(columns)
    if len(expected) != len(columns):
        raise ValueError("Duplicate column names are not supported.")
    for index, frame in enumerate(frames[1:], 1):
        actual = set(frame.columns)
        if actual != expected or len(frame.columns) != len(columns):
            name = names[index] if names else f"File {index + 1}"
            missing = ", ".join(map(str, expected - actual)) or "none"
            extra = ", ".join(map(str, actual - expected)) or "none"
            raise ValueError(
                f"{name}: columns do not match the first file.\n"
                f"Missing columns: {missing}.\nExtra columns: {extra}.\n"
                "Use files with the same column names. Their order may differ."
            )
    return pd.concat([frame.loc[:, columns] for frame in frames], ignore_index=True)
