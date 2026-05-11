from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_daily_filled_v2_clean.csv"
CALENDAR_CSV = BASE_DIR / "data" / "processed" / "academic_calendar_features.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_with_calendar_v2.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "monthly_sales_with_calendar_v2_report.txt"

FEATURE_COLS = [
    "is_start_semester",
    "is_end_semester",
    "is_exam",
    "is_vacation",
    "is_festival",
    "is_holiday_or_no_class",
]


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_CSV.exists():
        raise FileNotFoundError(f"Sales input not found: {SALES_CSV}")
    if not CALENDAR_CSV.exists():
        raise FileNotFoundError(f"Calendar input not found: {CALENDAR_CSV}")

    sales = pd.read_csv(SALES_CSV, low_memory=False)
    cal = pd.read_csv(CALENDAR_CSV, low_memory=False)

    if "date" not in sales.columns:
        raise KeyError("'date' not found in sales input.")
    if "date" not in cal.columns:
        raise KeyError("'date' not found in calendar input.")

    missing_features = [c for c in FEATURE_COLS if c not in cal.columns]
    if missing_features:
        raise KeyError(f"Missing calendar features: {missing_features}")

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    cal["date"] = pd.to_datetime(cal["date"], errors="coerce")
    sales = sales[sales["date"].notna()].copy()
    cal = cal[cal["date"].notna()].copy()

    merged = sales.merge(cal[["date"] + FEATURE_COLS], on="date", how="left")
    feature_missing_before_fill = merged[FEATURE_COLS].isna().sum()

    for col in FEATURE_COLS:
        merged[col] = merged[col].fillna(0).astype(int)

    out_df = merged.copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    lines: List[str] = []
    lines.append("Monthly Sales With Calendar V2 Report")
    lines.append(f"sales_input: {SALES_CSV.as_posix()}")
    lines.append(f"calendar_input: {CALENDAR_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append(f"row_count: {len(merged)}")
    lines.append(f"date_min: {merged['date'].min()}")
    lines.append(f"date_max: {merged['date'].max()}")
    lines.append(f"plu_code_unique_count: {int(merged['plu_code'].nunique())}")
    lines.append("")
    lines.append("[Calendar Feature Missing Count (before fillna)]")
    for col in FEATURE_COLS:
        lines.append(f"{col}: {int(feature_missing_before_fill[col])}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved merged csv: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Row count: {len(merged)}")
    print(f"Date range: {merged['date'].min()} ~ {merged['date'].max()}")


if __name__ == "__main__":
    main()
