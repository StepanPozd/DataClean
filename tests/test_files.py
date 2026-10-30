import hashlib
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook
from pandas.testing import assert_frame_equal

from app.core.data_processor import remove_duplicates
from app.core.file_handler import (
    EncodingReadError,
    FileReadError,
    canonical,
    excel_sheets,
    export_file,
    read_file,
)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "cp1251"])
def test_csv_encodings_and_unicode_paths(tmp_path, encoding):
    path = tmp_path / "Русские данные с пробелами.csv"
    frame = pd.DataFrame(
        {
            "Имя": ["Анна Смирнова", "Борис Иванов", "Екатерина Орлова"],
            "Город": ["Москва", "Казань", "Екатеринбург"],
            "Число": [1, 2, 3],
        }
    )
    frame.to_csv(path, index=False, encoding=encoding, sep=";")
    loaded = read_file(path, encoding=encoding)
    assert_frame_equal(loaded.frame, frame)
    assert_frame_equal(read_file(path).frame, frame)


@pytest.mark.parametrize("separator", [",", ";", "\t", "|"])
def test_csv_separators_and_quoted_fields(tmp_path, separator):
    frame = pd.DataFrame({"Name": ["a,b; c| d\t e", "two"], "Value": [1, 2]})
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False, sep=separator)
    assert_frame_equal(read_file(path).frame, frame)


def test_blank_csv_rows_preserved(tmp_path):
    path = tmp_path / "blank.csv"
    path.write_text("Name,Score\nАнна,1\n\nБорис,2\n", encoding="utf-8")
    result = read_file(path).frame
    assert len(result) == 3
    assert result.iloc[1].isna().all()


def test_csv_extra_fields_do_not_silently_become_an_index(tmp_path):
    path = tmp_path / "extra.csv"
    path.write_text("Name,Score\nАнна,1,unquoted extra field\n", encoding="utf-8")
    with pytest.raises(FileReadError, match="3 fields.*header has 2"):
        read_file(path)


def test_csv_unclosed_quote_is_rejected(tmp_path):
    path = tmp_path / "quote.csv"
    path.write_text('Name,Score\n"Анна,1\n', encoding="utf-8")
    with pytest.raises(FileReadError):
        read_file(path)


def test_existing_hard_link_to_source_is_protected(tmp_path):
    import os

    path = tmp_path / "source.csv"
    path.write_text("Name\nАнна\n", encoding="utf-8")
    alias = tmp_path / "alias.csv"
    os.link(path, alias)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="protected"):
        export_file(
            pd.DataFrame({"Name": ["Борис"]}), alias, protected_paths={canonical(path)}, overwrite=True
        )
    assert path.read_bytes() == before


def test_xlsx_sheets(tmp_path):
    path = tmp_path / "Таблица с листами.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"Name": ["Анна"]}).to_excel(writer, sheet_name="Первый", index=False)
        pd.DataFrame({"Name": ["Борис"]}).to_excel(writer, sheet_name="Второй", index=False)
    assert excel_sheets(path) == ["Первый", "Второй"]
    assert read_file(path).frame.iat[0, 0] == "Анна"
    assert read_file(path, sheet="Второй").frame.iat[0, 0] == "Борис"
    with pytest.raises(FileReadError, match="does not exist"):
        read_file(path, sheet="Missing")


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_exports_roundtrip_and_source_immutable(tmp_path, extension):
    source = tmp_path / "Исходные данные.xlsx"
    frame = pd.DataFrame({"Имя": ["Анна", "Анна", "Борис"], "Цена": [1, 1, 2]})
    frame.to_excel(source, index=False)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    result = remove_duplicates(read_file(source).frame).frame
    target = tmp_path / f"Результат очистки.{extension}"
    export_file(result, target, protected_paths={canonical(source)})
    assert_frame_equal(read_file(target).frame, result)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    if extension == "csv":
        assert target.read_bytes().startswith(b"\xef\xbb\xbf")


def test_source_overwrite_is_always_rejected(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text("Name\nАнна\n", encoding="utf-8")
    original = path.read_bytes()
    with pytest.raises(ValueError, match="protected"):
        export_file(
            pd.DataFrame({"Name": ["Борис"]}), path, protected_paths={canonical(path)}, overwrite=True
        )
    assert path.read_bytes() == original


def test_overwrite_requires_explicit_permission(tmp_path):
    path = tmp_path / "result.csv"
    path.write_text("original", encoding="utf-8")
    frame = pd.DataFrame({"Value": [2]})
    with pytest.raises(FileExistsError):
        export_file(frame, path)
    assert path.read_text() == "original"
    export_file(frame, path, overwrite=True)
    assert read_file(path).frame.iat[0, 0] == 2


def test_failed_export_preserves_existing_file_and_cleans_temporary(tmp_path):
    path = tmp_path / "result.xlsx"
    path.write_bytes(b"original")
    # Excel rejects timezone-aware timestamps, causing a failure during serialization.
    frame = pd.DataFrame({"Date": [pd.Timestamp("2026-01-01", tz="UTC")]})
    with pytest.raises(ValueError):
        export_file(frame, path, overwrite=True)
    assert path.read_bytes() == b"original"
    assert not list(tmp_path.glob(".dataclean-*"))


def test_formula_like_text_is_literal_in_xlsx(tmp_path):
    path = tmp_path / "formula.xlsx"
    export_file(pd.DataFrame({"Value": ["=1+1", '=HYPERLINK("https://example.test")']}), path)
    book = load_workbook(path, data_only=False)
    try:
        assert book.active["A2"].data_type == "s"
        assert book.active["A2"].value == "=1+1"
    finally:
        book.close()


@pytest.mark.parametrize("content", [b"", b"Name,Name\na,b\n", b",Score\na,1\n"])
def test_invalid_csv_headers(tmp_path, content):
    path = tmp_path / "invalid.csv"
    path.write_bytes(content)
    with pytest.raises(FileReadError):
        read_file(path)


def test_corrupt_xlsx(tmp_path):
    path = tmp_path / "broken.xlsx"
    path.write_bytes(b"not an excel workbook")
    with pytest.raises(FileReadError, match="Cannot read"):
        read_file(path)
    with pytest.raises(FileReadError, match="Cannot open"):
        excel_sheets(path)


def test_manual_wrong_encoding_has_recoverable_error(tmp_path):
    path = tmp_path / "legacy.csv"
    path.write_bytes("Имя\nАнна\n".encode("cp1251"))
    with pytest.raises(EncodingReadError):
        read_file(path, encoding="utf-8")


def test_unsupported_file_and_export_formats(tmp_path):
    with pytest.raises(FileReadError, match="CSV or XLSX"):
        read_file(tmp_path / "file.xls")
    with pytest.raises(ValueError, match="extension"):
        export_file(pd.DataFrame({"A": [1]}), tmp_path / "file.txt")


def test_examples_have_expected_statistics():
    from app.core.data_processor import statistics

    path = Path(__file__).resolve().parents[1] / "examples" / "customers_dirty.csv"
    result = statistics(read_file(path).frame)
    assert (result.rows, result.columns, result.missing, result.duplicates) == (10, 6, 9, 1)
