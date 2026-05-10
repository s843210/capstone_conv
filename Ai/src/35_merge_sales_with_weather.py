from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_INPUT_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar_timetable.csv"
WEATHER_INPUT_CSV = BASE_DIR / "data" / "processed" / "weather_features.csv"

OUTPUT_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar_timetable_weather.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "sales_weather_merge_report.txt"

WEATHER_COLS = ["avg_temp", "min_temp", "max_temp", "rainfall"]
TEMP_COLS = ["avg_temp", "min_temp", "max_temp"]


def read_csv_with_fallback(path: Path) -> tuple[pd.DataFrame, str]:
    try:
        return pd.read_csv(path, encoding="utf-8", low_memory=False), "utf-8"
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", low_memory=False), "cp949"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_INPUT_CSV.exists():
        raise FileNotFoundError(f"Sales input not found: {SALES_INPUT_CSV}")
    if not WEATHER_INPUT_CSV.exists():
        raise FileNotFoundError(f"Weather input not found: {WEATHER_INPUT_CSV}")

    sales, sales_enc = read_csv_with_fallback(SALES_INPUT_CSV)
    weather, weather_enc = read_csv_with_fallback(WEATHER_INPUT_CSV)

    if "date" not in sales.columns:
        raise KeyError("'date' column not found in sales_with_calendar_timetable.csv")
    if "date" not in weather.columns:
        raise KeyError("'date' column not found in weather_features.csv")

    missing_weather_cols = [c for c in WEATHER_COLS if c not in weather.columns]
    if missing_weather_cols:
        raise KeyError(f"Missing weather columns: {missing_weather_cols}")

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    weather["date"] = pd.to_datetime(weather["date"], errors="coerce")

    sales = sales[sales["date"].notna()].copy()
    weather = weather[weather["date"].notna()].copy()

    for col in WEATHER_COLS:
        weather[col] = pd.to_numeric(weather[col], errors="coerce")

    merged = sales.merge(weather[["date"] + WEATHER_COLS], on="date", how="left")

    temp_means = {col: float(merged[col].mean()) for col in TEMP_COLS}
    for col in TEMP_COLS:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(temp_means[col])

    merged["rainfall"] = pd.to_numeric(merged["rainfall"], errors="coerce").fillna(0)

    out_df = merged.copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    lines: List[str] = []
    lines.append("Sales + Weather Merge Report")
    lines.append(f"sales_input: {SALES_INPUT_CSV.as_posix()} (encoding: {sales_enc})")
    lines.append(f"weather_input: {WEATHER_INPUT_CSV.as_posix()} (encoding: {weather_enc})")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")

    lines.append(f"final_row_count: {len(merged)}")
    if len(merged) > 0:
        lines.append(f"date_min: {merged['date'].min()}")
        lines.append(f"date_max: {merged['date'].max()}")
    else:
        lines.append("date_min: None")
        lines.append("date_max: None")

    lines.append("")
    lines.append("[Weather Missing Count]")
    missing_counts = merged[WEATHER_COLS].isna().sum()
    for col in WEATHER_COLS:
        lines.append(f"{col}: {int(missing_counts[col])}")

    lines.append("")
    lines.append("[Weather Statistics]")
    if len(merged) == 0:
        lines.append("(empty dataframe)")
    else:
        stats = merged[WEATHER_COLS].describe().transpose()
        lines.append(stats.to_string())

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved merged dataset: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Final rows: {len(merged)}")


if __name__ == "__main__":
    main()
