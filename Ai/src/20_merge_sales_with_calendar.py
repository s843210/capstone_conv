from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CSV = BASE_DIR / "data" / "processed" / "final_sales_dataset.csv"
CALENDAR_CSV = BASE_DIR / "data" / "processed" / "academic_calendar_features.csv"

OUTPUT_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "sales_calendar_merge_report.txt"

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
        raise FileNotFoundError(f"Sales dataset not found: {SALES_CSV}")
    if not CALENDAR_CSV.exists():
        raise FileNotFoundError(f"Calendar feature dataset not found: {CALENDAR_CSV}")

    sales = pd.read_csv(SALES_CSV, low_memory=False)
    cal = pd.read_csv(CALENDAR_CSV, low_memory=False)

    if "date" not in sales.columns:
        raise KeyError("'date' column not found in final sales dataset.")
    if "date" not in cal.columns:
        raise KeyError("'date' column not found in calendar features.")

    missing_feature_cols = [c for c in FEATURE_COLS if c not in cal.columns]
    if missing_feature_cols:
        raise KeyError(f"Missing calendar feature columns: {missing_feature_cols}")

    # 2) convert date to datetime
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    cal["date"] = pd.to_datetime(cal["date"], errors="coerce")

    sales = sales[sales["date"].notna()].copy()
    cal = cal[cal["date"].notna()].copy()

    # 3) left merge on date
    merged = sales.merge(cal[["date"] + FEATURE_COLS], on="date", how="left")

    # 4) fill feature null with 0, 5) cast int
    for col in FEATURE_COLS:
        merged[col] = merged[col].fillna(0).astype(int)

    # Save with string date for portability
    out_df = merged.copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 8) report
    lines: list[str] = []
    lines.append("Sales + Calendar Merge Report")
    lines.append(f"sales_input: {SALES_CSV.as_posix()}")
    lines.append(f"calendar_input: {CALENDAR_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"final_row_count: {len(merged)}")
    lines.append(f"date_min: {merged['date'].min()}")
    lines.append(f"date_max: {merged['date'].max()}")
    lines.append("")
    lines.append("[Feature 1-count]")
    for col in FEATURE_COLS:
        lines.append(f"{col}: {int((merged[col] == 1).sum())}")
    lines.append("")
    lines.append("[Missing Count]")
    missing_counts = merged.isna().sum()
    for col, cnt in missing_counts.items():
        lines.append(f"{col}: {int(cnt)}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved merged dataset: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Final rows: {len(merged)}")
    print(f"Date range: {merged['date'].min()} ~ {merged['date'].max()}")


if __name__ == "__main__":
    main()
