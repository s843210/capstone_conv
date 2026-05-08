from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
TEST_FILE = (
    BASE_DIR / "data" / "raw" / "sales" / "sales_2024_03" / "240301" / "0301가공식품.xlsx"
)
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "sample_clean_sales.csv"
HEADER_KEYWORD = "카테고리/상품"


def find_real_header_row(file_path: Path, max_scan_rows: int = 50) -> Optional[int]:
    preview = pd.read_excel(file_path, header=None, nrows=max_scan_rows)
    for i in range(len(preview)):
        row = preview.iloc[i].astype(str).str.strip()
        if (row == HEADER_KEYWORD).any():
            return i
    return None


def extract_date(file_path: Path) -> str:
    # 1) Prefer yymmdd folder token, e.g. .../240301/...
    for part in file_path.parts:
        if re.fullmatch(r"\d{6}", part):
            yy = int(part[:2])
            year = 2000 + yy
            month = int(part[2:4])
            day = int(part[4:6])
            return f"{year:04d}-{month:02d}-{day:02d}"

    # 2) Fallback: from file name mmdd + year from sales_yyyy_mm
    m_file = re.match(r"^(\d{2})(\d{2})", file_path.stem)
    if m_file:
        month = int(m_file.group(1))
        day = int(m_file.group(2))
        for part in file_path.parts:
            m_month_folder = re.fullmatch(r"sales_(\d{4})_(\d{2})", part)
            if m_month_folder:
                year = int(m_month_folder.group(1))
                return f"{year:04d}-{month:02d}-{day:02d}"

    raise ValueError(f"Could not extract date from path/name: {file_path}")


def extract_category(file_path: Path) -> str:
    # e.g. 0301가공식품.xlsx -> 가공식품
    stem = file_path.stem
    category = re.sub(r"^\d{4}", "", stem).strip()
    if not category:
        raise ValueError(f"Could not extract category from filename: {file_path.name}")
    return category


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Remove line-breaks/spaces for matching (e.g. "매입\n합계")
    normalized_map = {}
    for col in df.columns:
        col_str = str(col)
        key = re.sub(r"\s+", "", col_str)
        normalized_map[key] = col

    rename_map = {}
    if "카테고리/상품" in normalized_map:
        rename_map[normalized_map["카테고리/상품"]] = "product_name"
    if "매입합계" in normalized_map:
        rename_map[normalized_map["매입합계"]] = "purchase_qty"
    if "매출합계" in normalized_map:
        rename_map[normalized_map["매출합계"]] = "sales_qty"

    df = df.rename(columns=rename_map)
    return df


def clean_rows(df: pd.DataFrame) -> pd.DataFrame:
    # Keep only rows with non-empty product_name.
    if "product_name" not in df.columns:
        raise KeyError("'product_name' column not found after rename.")

    work = df.copy()
    work["product_name"] = work["product_name"].astype(str).str.strip()
    work = work[work["product_name"].notna()]
    work = work[work["product_name"] != ""]
    work = work[work["product_name"].str.lower() != "nan"]

    # Drop summary rows likely not item-level.
    summary_pattern = r"(?:합계|총계|계$)"
    work = work[~work["product_name"].str.contains(summary_pattern, regex=True, na=False)]

    # Drop fully empty rows in selected numeric columns too.
    for col in ["purchase_qty", "sales_qty"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(how="all", subset=[c for c in ["purchase_qty", "sales_qty"] if c in work.columns])
    return work


def main() -> None:
    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_FILE}")

    header_row = find_real_header_row(TEST_FILE)
    if header_row is None:
        raise ValueError(f'Could not find header row with "{HEADER_KEYWORD}".')

    raw_df = pd.read_excel(TEST_FILE, header=header_row)
    df = normalize_columns(raw_df)

    required_after_rename = ["product_name", "purchase_qty", "sales_qty"]
    missing = [c for c in required_after_rename if c not in df.columns]
    if missing:
        raise KeyError(f"Required columns not found after normalization: {missing}")

    date_value = extract_date(TEST_FILE)
    category_value = extract_category(TEST_FILE)

    df = df[["product_name", "purchase_qty", "sales_qty"]].copy()
    df.insert(0, "category", category_value)
    df.insert(0, "date", date_value)

    df = clean_rows(df)
    df = df[["date", "category", "product_name", "purchase_qty", "sales_qty"]]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"Header row index: {header_row}")
    print(f"Date extracted: {date_value}")
    print(f"Category extracted: {category_value}")
    print("\n[Top 20 Rows]")
    print(df.head(20).to_string(index=False))
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Row count: {len(df)}")


if __name__ == "__main__":
    main()
