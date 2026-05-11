from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_daily_filled_v2.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_daily_filled_v2_clean.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "monthly_sales_daily_filled_v2_clean_report.txt"
CUTOFF_DATE = pd.Timestamp("2026-04-30")


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    original_rows = len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce")

    cutoff_df = df[df["date"] <= CUTOFF_DATE].copy()
    cutoff_rows = len(cutoff_df)
    removed_rows_after_cutoff = original_rows - cutoff_rows

    negative_mask = cutoff_df["sales_qty"] < 0
    negative_corrected_count = int(negative_mask.sum())
    cutoff_df.loc[negative_mask, "sales_qty"] = 0

    cutoff_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    if cutoff_df.empty:
        final_date_min = "N/A"
        final_date_max = "N/A"
        plu_unique = 0
        sales_zero_count = 0
    else:
        final_date_min = str(cutoff_df["date"].min())
        final_date_max = str(cutoff_df["date"].max())
        plu_unique = int(cutoff_df["plu_code"].nunique())
        sales_zero_count = int((cutoff_df["sales_qty"] == 0).sum())

    lines: List[str] = []
    lines.append("Monthly Sales Daily Filled V2 Clean Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append(f"cutoff_date: {CUTOFF_DATE.date()}")
    lines.append(f"original_rows: {original_rows}")
    lines.append(f"rows_after_cutoff: {cutoff_rows}")
    lines.append(f"removed_rows_after_2026_04_30: {removed_rows_after_cutoff}")
    lines.append(f"negative_sales_qty_corrected_rows: {negative_corrected_count}")
    lines.append(f"final_date_min: {final_date_min}")
    lines.append(f"final_date_max: {final_date_max}")
    lines.append(f"plu_code_unique_count: {plu_unique}")
    lines.append(f"sales_qty_zero_count: {sales_zero_count}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved clean csv: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cutoff: {cutoff_rows}")
    print(f"Removed rows after cutoff: {removed_rows_after_cutoff}")
    print(f"Negative corrected rows: {negative_corrected_count}")


if __name__ == "__main__":
    main()
