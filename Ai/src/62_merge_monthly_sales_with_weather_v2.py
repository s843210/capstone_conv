from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_with_calendar_timetable_v2.csv"
WEATHER_CSV = BASE_DIR / "data" / "processed" / "weather_features.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_with_calendar_timetable_weather_v2.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "monthly_sales_with_weather_v2_report.txt"

WEATHER_COLS = ["avg_temp", "min_temp", "max_temp", "rainfall"]


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_CSV.exists():
        raise FileNotFoundError(f"Sales input not found: {SALES_CSV}")
    if not WEATHER_CSV.exists():
        raise FileNotFoundError(f"Weather input not found: {WEATHER_CSV}")

    sales = pd.read_csv(SALES_CSV, low_memory=False)
    weather = pd.read_csv(WEATHER_CSV, low_memory=False)

    if "date" not in sales.columns:
        raise KeyError("'date' not found in sales input.")
    if "date" not in weather.columns:
        raise KeyError("'date' not found in weather input.")

    missing_weather = [c for c in WEATHER_COLS if c not in weather.columns]
    if missing_weather:
        raise KeyError(f"Missing weather columns: {missing_weather}")

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    weather["date"] = pd.to_datetime(weather["date"], errors="coerce")
    sales = sales[sales["date"].notna()].copy()
    weather = weather[weather["date"].notna()].copy()

    for col in WEATHER_COLS:
        weather[col] = pd.to_numeric(weather[col], errors="coerce")

    merged = sales.merge(weather[["date"] + WEATHER_COLS], on="date", how="left")
    missing_before_fill = merged[WEATHER_COLS].isna().sum()

    temp_cols = ["avg_temp", "min_temp", "max_temp"]
    for col in temp_cols:
        fill_value = float(merged[col].mean(skipna=True))
        merged[col] = merged[col].fillna(fill_value)
    merged["rainfall"] = merged["rainfall"].fillna(0.0)

    out_df = merged.copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    lines: List[str] = []
    lines.append("Monthly Sales With Weather V2 Report")
    lines.append(f"sales_input: {SALES_CSV.as_posix()}")
    lines.append(f"weather_input: {WEATHER_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append(f"row_count: {len(merged)}")
    lines.append(f"date_min: {merged['date'].min()}")
    lines.append(f"date_max: {merged['date'].max()}")
    lines.append(f"plu_code_unique_count: {int(merged['plu_code'].nunique())}")
    lines.append("")
    lines.append("[Missing Count (before fillna)]")
    for col in WEATHER_COLS:
        lines.append(f"{col}: {int(missing_before_fill[col])}")
    lines.append("")
    lines.append("[Applied Fill Strategy]")
    lines.append("- avg_temp/min_temp/max_temp: filled with overall mean")
    lines.append("- rainfall: filled with 0")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved merged csv: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Row count: {len(merged)}")
    print(f"Date range: {merged['date'].min()} ~ {merged['date'].max()}")


if __name__ == "__main__":
    main()
