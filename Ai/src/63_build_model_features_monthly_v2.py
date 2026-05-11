from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_with_calendar_timetable_weather_v2.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_monthly_v2.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "model_features_monthly_v2_report.txt"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    required_cols = {
        "date",
        "plu_code",
        "sales_qty",
        "avg_temp",
        "min_temp",
        "max_temp",
        "rainfall",
        "is_vacation",
        "is_exam",
        "is_festival",
        "is_start_semester",
        "is_end_semester",
        "is_holiday_or_no_class",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce")
    for c in ["avg_temp", "min_temp", "max_temp", "rainfall"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df[df["date"].notna()].copy()
    df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)

    # Date features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    # Lag features
    g = df.groupby("plu_code", group_keys=False)
    df["sales_lag_1"] = g["sales_qty"].shift(1)
    df["sales_lag_7"] = g["sales_qty"].shift(7)

    # Rolling features with shift(1) to avoid leakage
    shifted_sales = g["sales_qty"].shift(1)
    df["rolling_mean_7"] = shifted_sales.groupby(df["plu_code"]).transform(
        lambda s: s.rolling(window=7, min_periods=7).mean()
    )
    df["rolling_mean_14"] = shifted_sales.groupby(df["plu_code"]).transform(
        lambda s: s.rolling(window=14, min_periods=14).mean()
    )
    df["rolling_mean_28"] = shifted_sales.groupby(df["plu_code"]).transform(
        lambda s: s.rolling(window=28, min_periods=28).mean()
    )

    # Target (next day sales)
    df["target_sales"] = g["sales_qty"].shift(-1)

    # Binary weather features
    df["is_rainy"] = (df["rainfall"] > 0).astype(int)
    df["is_hot"] = (df["avg_temp"] >= 27).astype(int)
    df["is_cold"] = (df["avg_temp"] <= 5).astype(int)

    # Academic simplification
    df["is_semester"] = (df["is_vacation"] != 1).astype(int)

    # Drop continuous weather cols
    df = df.drop(columns=["avg_temp", "min_temp", "max_temp", "rainfall"])

    # Drop old academic cols
    df = df.drop(
        columns=[
            "is_exam",
            "is_festival",
            "is_start_semester",
            "is_end_semester",
            "is_holiday_or_no_class",
            "is_vacation",
        ]
    )

    # purchase_qty is not in input; no action needed. Drop missing rows.
    df = df.dropna().copy()

    out_df = df.copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # Build report
    lines: List[str] = []
    lines.append("Model Features Monthly V2 Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append(f"final_row_count: {len(df)}")
    if len(df) > 0:
        lines.append(f"date_min: {df['date'].min()}")
        lines.append(f"date_max: {df['date'].max()}")
        lines.append(f"plu_code_unique_count: {int(df['plu_code'].nunique())}")
        lines.append("target_sales_stats:")
        stats = df["target_sales"].agg(["min", "max", "mean", "median"])
        lines.append(f"- min: {stats['min']}")
        lines.append(f"- max: {stats['max']}")
        lines.append(f"- mean: {stats['mean']}")
        lines.append(f"- median: {stats['median']}")
    else:
        lines.append("date_min: N/A")
        lines.append("date_max: N/A")
        lines.append("plu_code_unique_count: 0")
        lines.append("target_sales_stats: N/A")
    lines.append("feature_columns:")
    for c in df.columns.tolist():
        lines.append(f"- {c}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved model features: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()
