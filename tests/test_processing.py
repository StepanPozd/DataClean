import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from app.core.data_manager import DataManager, Snapshot
from app.core.data_processor import (
    fill_missing,
    merge_frames,
    remove_duplicates,
    remove_empty_rows,
    statistics,
    trim_whitespace,
)


def test_statistics(dirty_frame):
    result = statistics(dirty_frame)
    assert (result.rows, result.columns, result.missing, result.duplicates) == (6, 3, 5, 1)


def test_duplicates_keeps_first_and_does_not_mutate(dirty_frame):
    original = dirty_frame.copy(deep=True)
    result = remove_duplicates(dirty_frame)
    assert result.affected == 1
    assert len(result.frame) == 5
    assert result.frame.index.tolist() == list(range(5))
    assert result.frame.iloc[0, 0] == "  Анна  "
    assert_frame_equal(dirty_frame, original)


def test_empty_rows_includes_spaces_but_preserves_zero_and_false(dirty_frame):
    result = remove_empty_rows(dirty_frame)
    assert result.affected == 2
    assert len(result.frame) == 4
    assert result.frame.iloc[-1]["Score"] == 0
    frame = pd.DataFrame({"value": [False, 0, "", " ", None]})
    assert len(remove_empty_rows(frame).frame) == 2


def test_trim_only_changes_text_boundaries(dirty_frame):
    result = trim_whitespace(dirty_frame)
    assert result.frame.iloc[0]["Name"] == "Анна"
    assert result.frame.iloc[0]["City"] == "Москва"
    assert result.frame.iloc[4]["Name"] == ""
    assert result.frame.iloc[0]["Score"] == 10
    assert pd.isna(result.frame.iloc[3]["Name"])
    assert trim_whitespace(pd.DataFrame({"Name": [" Анна  Смирнова "]})).frame.iat[0, 0] == "Анна  Смирнова"


@pytest.mark.parametrize("replacement", [0, "Unknown", "Нет данных", 1.5])
def test_fill_missing_supports_mixed_types(dirty_frame, replacement):
    result = fill_missing(dirty_frame, replacement)
    assert result.frame.isna().sum().sum() == 0
    assert result.affected == 3
    assert result.frame.iloc[1]["Score"] == replacement
    assert result.frame.iloc[4]["Name"] == "  "
    assert dirty_frame.isna().sum().sum() == 5


def test_fill_rejects_empty_value(dirty_frame):
    with pytest.raises(ValueError, match="non-empty"):
        fill_missing(dirty_frame, "")


def test_undo_reset_and_reset_itself_is_undoable(dirty_frame):
    manager = DataManager()
    baseline = Snapshot.prepare(dirty_frame.copy(deep=True))
    manager.load(baseline, "example.csv")
    cleaned = Snapshot.prepare(remove_duplicates(baseline.frame).frame)
    manager.apply(cleaned)
    assert manager.dirty
    manager.undo()
    assert manager.current is baseline
    assert not manager.dirty
    manager.apply(cleaned)
    manager.reset()
    assert manager.current is baseline
    assert not manager.dirty
    manager.undo()
    assert manager.current is cleaned
    assert_frame_equal(manager.original.frame, dirty_frame)


def test_undo_after_export_is_marked_dirty(dirty_frame):
    manager = DataManager()
    manager.load(Snapshot.prepare(dirty_frame), "data.csv")
    manager.apply(Snapshot.prepare(remove_duplicates(dirty_frame).frame))
    manager.mark_saved()
    assert not manager.dirty
    manager.undo()
    assert manager.dirty


def test_undo_limit_and_new_import_clears_previous_state(dirty_frame):
    manager = DataManager()
    manager.load(Snapshot.prepare(dirty_frame), "first.csv")
    for _ in range(15):
        manager.apply(Snapshot.prepare(dirty_frame.copy()))
    assert len(manager.undo_stack) == 10
    manager.load(Snapshot.prepare(pd.DataFrame({"new": [1]})), "second.csv")
    assert not manager.undo_stack
    assert manager.current.stats.rows == 1
    assert not manager.dirty


def test_merge_reorders_columns_and_keeps_sources(dirty_frame):
    other = dirty_frame.iloc[:2, ::-1].copy()
    original = other.copy(deep=True)
    result = merge_frames([dirty_frame, other])
    assert list(result.columns) == list(dirty_frame.columns)
    assert len(result) == 8
    assert result.iloc[6]["Name"] == dirty_frame.iloc[0]["Name"]
    assert_frame_equal(other, original)


def test_merge_explains_column_mismatch(dirty_frame):
    with pytest.raises(ValueError, match="wrong.csv.*columns do not match") as error:
        merge_frames([dirty_frame, pd.DataFrame({"Other": [1]})], ["first.csv", "wrong.csv"])
    assert "Missing columns" in str(error.value)
    assert "Extra columns: Other" in str(error.value)


def test_merge_requires_two_files(dirty_frame):
    with pytest.raises(ValueError, match="at least two"):
        merge_frames([dirty_frame])


def test_header_only_dataframe():
    frame = pd.DataFrame(columns=["Name", "Amount"])
    assert statistics(frame).rows == 0
    assert remove_duplicates(frame).affected == 0
    assert remove_empty_rows(frame).affected == 0
    assert trim_whitespace(frame).affected == 0
    assert fill_missing(frame, "Unknown").affected == 0
