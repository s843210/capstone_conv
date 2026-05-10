from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar_timetable_weather.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_weather.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "model_features_weather_report.txt"

WEATHER_COLS = ["avg_temp", "min_temp", "max_temp", "rainfall"]


def read_csv_with_fallback(path: Path) -> tuple[pd.DataFrame, str]:
    try:
        return pd.read_csv(path, encoding="utf-8", low_memory=False), "utf-8"
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", low_memory=False), "cp949"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df, used_encoding = read_csv_with_fallback(INPUT_CSV)

    required_cols = {"date", "plu_code", "sales_qty", *WEATHER_COLS}
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
    for col in WEATHER_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # plu_code cleanup
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    df = df[(df["plu_code"] != "") & (df["plu_code"].str.lower() != "nan")].copy()

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

    # 5) leak-safe rolling means: shift(1) before rolling
    shifted_sales = grp["sales_qty"].shift(1)
    df["rolling_mean_7"] = shifted_sales.groupby(df["plu_code"]).rolling(7).mean().reset_index(level=0, drop=True)
    df["rolling_mean_14"] = shifted_sales.groupby(df["plu_code"]).rolling(14).mean().reset_index(level=0, drop=True)
    df["rolling_mean_28"] = shifted_sales.groupby(df["plu_code"]).rolling(28).mean().reset_index(level=0, drop=True)

    # 6) target
    df["target_sales"] = grp["sales_qty"].shift(-1)

    # 9) drop rows with missing in key model columns
    drop_required: List[str] = [
        "sales_lag_1",
        "sales_lag_7",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_28",
        "target_sales",
        *WEATHER_COLS,
    ]
    before_drop = len(df)
    model_df = df.dropna(subset=drop_required).copy()
    dropped_rows = before_drop - len(model_df)

    # 10) save
    save_df = model_df.copy()
    save_df["date"] = save_df["date"].dt.strftime("%Y-%m-%d")
    save_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 11~12) report
    lines: List[str] = []
    lines.append("Model Features Weather Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()} (encoding: {used_encoding})")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"initial_rows: {before_drop}")
    lines.append(f"final_rows: {len(model_df)}")
    lines.append(f"rows_dropped_by_nan_filters: {dropped_rows}")
    if len(model_df) > 0:
        lines.append(f"date_min: {model_df['date'].min()}")
        lines.append(f"date_max: {model_df['date'].max()}")
    else:
        lines.append("date_min: None")
        lines.append("date_max: None")
    lines.append(f"plu_code_unique_count: {model_df['plu_code'].nunique()}")

    lines.append("")
    lines.append("[target_sales stats]")
    if len(model_df) > 0:
        lines.append(f"count: {model_df['target_sales'].count()}")
        lines.append(f"min: {model_df['target_sales'].min()}")
        lines.append(f"max: {model_df['target_sales'].max()}")
        lines.append(f"mean: {model_df['target_sales'].mean()}")
        lines.append(f"median: {model_df['target_sales'].median()}")
        lines.append(f"std: {model_df['target_sales'].std()}")
    else:
        lines.append("(empty dataframe)")

    lines.append("")
    lines.append("[weather feature missing count]")
    weather_missing = model_df[WEATHER_COLS].isna().sum()
    for col in WEATHER_COLS:
        lines.append(f"{col}: {int(weather_missing[col])}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved model features: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Final rows: {len(model_df)}")


if __name__ == "__main__":
    main()
