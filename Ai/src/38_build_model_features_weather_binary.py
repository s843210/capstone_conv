from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar_timetable_weather.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_weather_binary.csv"

WEATHER_CONT_COLS = ["avg_temp", "min_temp", "max_temp", "rainfall"]
WEATHER_BINARY_COLS = ["is_rainy", "is_hot", "is_cold"]


def read_csv_with_fallback(path: Path) -> tuple[pd.DataFrame, str]:
    try:
        return pd.read_csv(path, encoding="utf-8", low_memory=False), "utf-8"
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", low_memory=False), "cp949"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df, _ = read_csv_with_fallback(INPUT_CSV)

    required_cols = {"date", "plu_code", "sales_qty", *WEATHER_CONT_COLS}
    missing = required_cols - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    # 1) date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    # sales numeric cleanup
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce")
    df = df[df["sales_qty"].notna()].copy()

    # weather numeric cleanup
    for col in WEATHER_CONT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # plu_code cleanup
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    df = df[(df["plu_code"] != "") & (df["plu_code"].str.lower() != "nan")].copy()

    # 1) binary weather features
    df["is_rainy"] = (df["rainfall"] > 0).astype(int)
    df["is_hot"] = (df["avg_temp"] >= 27).astype(int)
    df["is_cold"] = (df["avg_temp"] <= 5).astype(int)

    # 2) remove continuous weather columns from model input dataset
    df = df.drop(columns=WEATHER_CONT_COLS)

    # 2) sort by plu/date
    df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)

    # 3) date features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    # 4) lag features
    grp = df.groupby("plu_code", group_keys=False)
    df["sales_lag_1"] = grp["sales_qty"].shift(1)
    df["sales_lag_7"] = grp["sales_qty"].shift(7)

    # 5) leakage prevention: shift(1) before rolling
    shifted_sales = grp["sales_qty"].shift(1)
    df["rolling_mean_7"] = shifted_sales.groupby(df["plu_code"]).rolling(7).mean().reset_index(level=0, drop=True)
    df["rolling_mean_14"] = shifted_sales.groupby(df["plu_code"]).rolling(14).mean().reset_index(level=0, drop=True)
    df["rolling_mean_28"] = shifted_sales.groupby(df["plu_code"]).rolling(28).mean().reset_index(level=0, drop=True)

    # 6) target
    df["target_sales"] = grp["sales_qty"].shift(-1)

    # drop NaNs from key model columns
    drop_required: List[str] = [
        "sales_lag_1",
        "sales_lag_7",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_28",
        "target_sales",
        *WEATHER_BINARY_COLS,
    ]
    model_df = df.dropna(subset=drop_required).copy()

    # save
    save_df = model_df.copy()
    save_df["date"] = save_df["date"].dt.strftime("%Y-%m-%d")
    save_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"Saved model features (binary weather): {OUTPUT_CSV}")
    print(f"Final rows: {len(model_df)}")


if __name__ == "__main__":
    main()
