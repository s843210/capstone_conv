from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TEST_FILE = (
    BASE_DIR / "data" / "raw" / "sales" / "sales_2024_03" / "240301" / "0301가공식품.xlsx"
)
TARGET_HEADER_TEXT = "카테고리/상품"


def find_header_row(file_path: Path, sheet_name: str = 0, max_scan_rows: int = 50) -> Optional[int]:
    preview_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=max_scan_rows)

    for row_idx in range(len(preview_df)):
        row_values = preview_df.iloc[row_idx].astype(str).str.strip()
        if (row_values == TARGET_HEADER_TEXT).any():
            return row_idx
    return None


def main() -> None:
    test_file = DEFAULT_TEST_FILE
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return

    print(f"Test file: {test_file}")
    header_row = find_header_row(test_file)

    if header_row is None:
        print(f'Header row containing "{TARGET_HEADER_TEXT}" was not found.')
        return

    print(f'Real header row index found: {header_row}')
    df = pd.read_excel(test_file, header=header_row)

    print("\n[Columns]")
    print(list(df.columns))

    print("\n[Top 10 Rows]")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
