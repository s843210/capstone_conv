from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_DIR = BASE_DIR / "data" / "raw" / "sales"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "daily_sales_raw_v2.csv"
LOG_PATH = BASE_DIR / "outputs" / "reports" / "merge_sales_log_v2.txt"

HEADER_KEYWORD = "카테고리/상품"
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}


def find_real_header_row(file_path: Path, max_scan_rows: int = 50) -> Optional[int]:
    preview = pd.read_excel(file_path, header=None, nrows=max_scan_rows)
    for i in range(len(preview)):
        row = preview.iloc[i].astype(str).str.strip()
        if (row == HEADER_KEYWORD).any():
            return i
    return None


def extract_date(file_path: Path) -> str:
    # Rule 1: if parent folder token is YYMMDD (e.g. 240301), treat as daily.
    for part in file_path.parts:
        if re.fullmatch(r"\d{6}", part):
            yy = int(part[:2])
            mm = int(part[2:4])
            dd = int(part[4:6])
            return f"{2000 + yy:04d}-{mm:02d}-{dd:02d}"

    # Rule 2: if filename starts with 4 digits YYMM (e.g. 2410가공식품.xlsx), treat as monthly.
    m_yymm = re.match(r"^(\d{2})(\d{2})", file_path.stem)
    if m_yymm:
        yy = int(m_yymm.group(1))
        mm = int(m_yymm.group(2))
        return f"{2000 + yy:04d}-{mm:02d}-01"

    raise ValueError("Could not extract date from file path or name.")


def extract_category(file_path: Path) -> str:
    # Strip first 4 digits prefix (YYMM or MMDD) and keep the rest.
    category = re.sub(r"^\d{4}", "", file_path.stem).strip()
    if not category:
        raise ValueError("Could not extract category from file name.")
    return category


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized_map: dict[str, str] = {}
    for col in df.columns:
        key = re.sub(r"\s+", "", str(col))
        normalized_map[key] = col

    rename_map: dict[str, str] = {}
    if "카테고리/상품" in normalized_map:
        rename_map[normalized_map["카테고리/상품"]] = "product_name"
    if "매입합계" in normalized_map:
        rename_map[normalized_map["매입합계"]] = "purchase_qty"
    if "매출합계" in normalized_map:
        rename_map[normalized_map["매출합계"]] = "sales_qty"

    return df.rename(columns=rename_map)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["product_name", "purchase_qty", "sales_qty"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns after normalization: {missing}")

    work = df[required_cols].copy()
    work["product_name"] = work["product_name"].astype(str).str.strip()
    work = work[work["product_name"].notna()]
    work = work[work["product_name"] != ""]
    work = work[work["product_name"].str.lower() != "nan"]

    summary_pattern = r"(?:합계|총계|계$)"
    work = work[~work["product_name"].str.contains(summary_pattern, regex=True, na=False)]

    work["purchase_qty"] = pd.to_numeric(work["purchase_qty"], errors="coerce")
    work["sales_qty"] = pd.to_numeric(work["sales_qty"], errors="coerce")
    work = work.dropna(how="all", subset=["purchase_qty", "sales_qty"])
    return work


def process_one_file(file_path: Path) -> pd.DataFrame:
    header_row = find_real_header_row(file_path)
    if header_row is None:
        raise ValueError(f'Header row with "{HEADER_KEYWORD}" not found.')

    raw_df = pd.read_excel(file_path, header=header_row)
    normalized = normalize_columns(raw_df)
    cleaned = clean_dataframe(normalized)

    date_value = extract_date(file_path)
    category_value = extract_category(file_path)
    source_file_value = file_path.relative_to(BASE_DIR).as_posix()

    cleaned.insert(0, "category", category_value)
    cleaned.insert(0, "date", date_value)
    cleaned["source_file"] = source_file_value

    return cleaned[
        ["date", "category", "product_name", "purchase_qty", "sales_qty", "source_file"]
    ].copy()


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    all_files = sorted(
        [p for p in SALES_DIR.rglob("*") if p.is_file() and p.suffix.lower() in EXCEL_EXTENSIONS]
    )

    merged_frames: list[pd.DataFrame] = []
    success_count = 0
    failed: list[tuple[str, str]] = []

    for file_path in all_files:
        try:
            processed = process_one_file(file_path)
            merged_frames.append(processed)
            success_count += 1
        except Exception as exc:
            rel = file_path.relative_to(BASE_DIR).as_posix()
            failed.append((rel, str(exc)))

    if merged_frames:
        merged_df = pd.concat(merged_frames, ignore_index=True)
    else:
        merged_df = pd.DataFrame(
            columns=["date", "category", "product_name", "purchase_qty", "sales_qty", "source_file"]
        )

    merged_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    parsed_dates = pd.to_datetime(merged_df["date"], errors="coerce") if not merged_df.empty else pd.Series(dtype="datetime64[ns]")
    nat_count = int(parsed_dates.isna().sum()) if not merged_df.empty else 0
    date_min = parsed_dates.min() if not merged_df.empty else None
    date_max = parsed_dates.max() if not merged_df.empty else None

    log_lines: list[str] = []
    log_lines.append("Merge Sales Files Log V2")
    log_lines.append(f"target_directory: {SALES_DIR.as_posix()}")
    log_lines.append(f"total_target_files: {len(all_files)}")
    log_lines.append(f"success_files: {success_count}")
    log_lines.append(f"failed_files: {len(failed)}")
    log_lines.append(f"final_saved_rows: {len(merged_df)}")
    log_lines.append(f"date_min: {date_min}")
    log_lines.append(f"date_max: {date_max}")
    log_lines.append(f"date_nat_count: {nat_count}")
    log_lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    log_lines.append("")
    log_lines.append("[Failed Files]")
    if failed:
        for path_text, reason in failed:
            log_lines.append(f"- file: {path_text}")
            log_lines.append(f"  reason: {reason}")
    else:
        log_lines.append("None")

    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")

    print(f"Total target files: {len(all_files)}")
    print(f"Success files: {success_count}")
    print(f"Failed files: {len(failed)}")
    print(f"Final saved rows: {len(merged_df)}")
    print(f"Date min: {date_min}")
    print(f"Date max: {date_max}")
    print(f"Date NaT count: {nat_count}")
    print(f"Saved CSV: {OUTPUT_CSV}")
    print(f"Saved log: {LOG_PATH}")


if __name__ == "__main__":
    main()
