from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CALENDAR_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar.csv"
TIMETABLE_FEATURES_CSV = BASE_DIR / "data" / "processed" / "timetable_features.csv"

OUTPUT_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar_timetable.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "sales_timetable_merge_report.txt"

TT_FEATURE_COLS = [
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

    if not SALES_CALENDAR_CSV.exists():
        raise FileNotFoundError(f"Sales+calendar file not found: {SALES_CALENDAR_CSV}")
    if not TIMETABLE_FEATURES_CSV.exists():
        raise FileNotFoundError(f"Timetable feature file not found: {TIMETABLE_FEATURES_CSV}")

    sales = pd.read_csv(SALES_CALENDAR_CSV, low_memory=False)
    tt = pd.read_csv(TIMETABLE_FEATURES_CSV, low_memory=False)

    if "date" not in sales.columns:
        raise KeyError("'date' column not found in sales_with_calendar.csv")
    if "date" not in tt.columns:
        raise KeyError("'date' column not found in timetable_features.csv")

    missing_tt = [c for c in TT_FEATURE_COLS if c not in tt.columns]
    if missing_tt:
        raise KeyError(f"Missing timetable feature columns: {missing_tt}")

    # 2) convert date
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    tt["date"] = pd.to_datetime(tt["date"], errors="coerce")
    sales = sales[sales["date"].notna()].copy()
    tt = tt[tt["date"].notna()].copy()

    # 3) left merge
    merged = sales.merge(tt[["date"] + TT_FEATURE_COLS], on="date", how="left")

    # 4) fill null with 0, 5) numeric conversion
    for col in TT_FEATURE_COLS:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    # Save with date string
    out_df = merged.copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 8) report
    lines: list[str] = []
    lines.append("Sales + Timetable Merge Report")
    lines.append(f"sales_calendar_input: {SALES_CALENDAR_CSV.as_posix()}")
    lines.append(f"timetable_input: {TIMETABLE_FEATURES_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"final_row_count: {len(merged)}")
    lines.append(f"date_min: {merged['date'].min()}")
    lines.append(f"date_max: {merged['date'].max()}")
    lines.append("")
    lines.append("[class_count stats]")
    lines.append(f"class_count_min: {float(merged['class_count'].min())}")
    lines.append(f"class_count_max: {float(merged['class_count'].max())}")
    lines.append(f"class_count_mean: {float(merged['class_count'].mean())}")
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
    print(
        "class_count stats: "
        f"min={float(merged['class_count'].min())}, "
        f"max={float(merged['class_count'].max())}, "
        f"mean={float(merged['class_count'].mean())}"
    )


if __name__ == "__main__":
    main()
