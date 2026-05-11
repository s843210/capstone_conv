from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_with_calendar_v2.csv"
TIMETABLE_CSV = BASE_DIR / "data" / "processed" / "timetable_features.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_with_calendar_timetable_v2.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "monthly_sales_with_timetable_v2_report.txt"

FEATURE_COLS = [
    "class_count",
    "monday_class_count",
    "tuesday_class_count",
    "wednesday_class_count",
    "thursday_class_count",
    "friday_class_count",
]


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_CSV.exists():
        raise FileNotFoundError(f"Sales input not found: {SALES_CSV}")
    if not TIMETABLE_CSV.exists():
        raise FileNotFoundError(f"Timetable input not found: {TIMETABLE_CSV}")

    sales = pd.read_csv(SALES_CSV, low_memory=False)
    timetable = pd.read_csv(TIMETABLE_CSV, low_memory=False)

    if "date" not in sales.columns:
        raise KeyError("'date' not found in sales input.")
    if "date" not in timetable.columns:
        raise KeyError("'date' not found in timetable input.")

    missing_features = [c for c in FEATURE_COLS if c not in timetable.columns]
    if missing_features:
        raise KeyError(f"Missing timetable feature columns: {missing_features}")

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    timetable["date"] = pd.to_datetime(timetable["date"], errors="coerce")

    sales = sales[sales["date"].notna()].copy()
    timetable = timetable[timetable["date"].notna()].copy()

    merged = sales.merge(timetable[["date"] + FEATURE_COLS], on="date", how="left")
    missing_before_fill = merged[FEATURE_COLS].isna().sum()

    for col in FEATURE_COLS:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    out_df = merged.copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    class_stats = merged["class_count"].agg(["min", "max", "mean", "median"])

    lines: List[str] = []
    lines.append("Monthly Sales With Timetable V2 Report")
    lines.append(f"sales_input: {SALES_CSV.as_posix()}")
    lines.append(f"timetable_input: {TIMETABLE_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append(f"row_count: {len(merged)}")
    lines.append(f"date_min: {merged['date'].min()}")
    lines.append(f"date_max: {merged['date'].max()}")
    lines.append(f"plu_code_unique_count: {int(merged['plu_code'].nunique())}")
    lines.append("")
    lines.append("[class_count stats]")
    lines.append(f"min: {class_stats['min']}")
    lines.append(f"max: {class_stats['max']}")
    lines.append(f"mean: {class_stats['mean']}")
    lines.append(f"median: {class_stats['median']}")
    lines.append("")
    lines.append("[Missing Count (before fillna)]")
    for col in FEATURE_COLS:
        lines.append(f"{col}: {int(missing_before_fill[col])}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved merged csv: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Row count: {len(merged)}")
    print(f"Date range: {merged['date'].min()} ~ {merged['date'].max()}")


if __name__ == "__main__":
    main()
