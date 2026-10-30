# Synthetic example data

All names, records and `example.test` addresses are fictional.

| File | Purpose |
| --- | --- |
| `customers_dirty.csv` | 10 rows: duplicates, missing values, whitespace, Cyrillic, numbers and booleans |
| `customers_workbook.xlsx` | Two sheets: `Customers` (same dirty dataset) and `New customers` |
| `customers_more.csv` | Three compatible records for merging |
| `customers_reordered.xlsx` | Same fields in reverse order; merge aligns by name |
| `legacy_cyrillic.csv` | Semicolon-delimited Windows-1251 text |
| `incompatible_columns.csv` | Intentional column mismatch for the merge error dialog |

Regenerate from the project root with `.venv\Scripts\python.exe examples\generate_examples.py`.
The dirty CSV initially has 10 rows, 6 columns, 9 missing cells and 1 duplicate row.
