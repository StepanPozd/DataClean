"""Regenerate synthetic fixtures. Never run this against user documents."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent


def generate():
    ROOT.mkdir(exist_ok=True)
    columns = ["ID", "Name", "City", "Revenue", "Active", "Email"]
    first = [1001, "  Анна Смирнова  ", "  Москва", 1250.5, True, "anna@example.test "]
    rows = [
        first,
        [1002, "Иван Петров", "Казань ", 890.0, True, "ivan@example.test"],
        [1003, "  Мария Волкова", "Алматы", None, False, "maria@example.test"],
        first.copy(),
        [None] * 6,
        [1004, "Alex Morgan", "London", 2450.75, True, None],
        [1005, "Олег Ким", None, 0, False, "oleg@example.test"],
        [" ", "   ", "\t", " ", " ", " "],
        [1006, "Елена Новикова ", "Астана", 1870.0, True, "elena@example.test"],
        [1007, "Дмитрий Соколов", "Москва", 540.25, False, "dmitry@example.test"],
    ]
    dirty = pd.DataFrame(rows, columns=columns)
    extra = pd.DataFrame(
        [
            [1008, "София Орлова", "Омск", 700.0, True, "sofia@example.test"],
            [1009, "  Николай Белов ", "Томск", 990.5, True, None],
            [1010, "Olivia Chen", "Singapore", 1550.0, False, "olivia@example.test"],
        ],
        columns=columns,
    )
    dirty.to_csv(ROOT / "customers_dirty.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(ROOT / "customers_workbook.xlsx", engine="openpyxl") as writer:
        dirty.to_excel(writer, index=False, sheet_name="Customers")
        extra.to_excel(writer, index=False, sheet_name="New customers")
    extra.to_csv(ROOT / "customers_more.csv", index=False, encoding="utf-8-sig")
    extra[columns[::-1]].to_excel(ROOT / "customers_reordered.xlsx", index=False)
    pd.DataFrame(
        {"Имя": ["Анна", "Борис", "Екатерина", "Дмитрий"], "Город": ["Москва", "Казань", "Воронеж", "Омск"]}
    ).to_csv(ROOT / "legacy_cyrillic.csv", index=False, encoding="cp1251", sep=";")
    pd.DataFrame({"Different_ID": [1, 2], "Description": ["A", "B"]}).to_csv(
        ROOT / "incompatible_columns.csv", index=False, encoding="utf-8-sig"
    )


if __name__ == "__main__":
    generate()
    print(f"Synthetic examples generated in {ROOT}")
