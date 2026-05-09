from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar_timetable.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "model_features.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "model_features_report.txt"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    required_cols = {"date", "plu_code", "sales_qty"}
    missing = required_cols - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    # 2) date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    # ensure numeric sales
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce")
    df = df[df["sales_qty"].notna()].copy()

    # normalize key
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    df = df[(df["plu_code"] != "") & (df["plu_code"].str.lower() != "nan")].copy()

    # 3) sort by plu/date
    df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)

    # 4) date features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday  # Monday=0
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    # 5) lag / rolling features by product
    grp = df.groupby("plu_code", group_keys=False)
    df["sales_lag_1"] = grp["sales_qty"].shift(1)
    df["sales_lag_7"] = grp["sales_qty"].shift(7)

    # 7) leakage prevention: shift(1) before rolling
    shifted_sales = grp["sales_qty"].shift(1)
    df["rolling_mean_7"] = shifted_sales.groupby(df["plu_code"]).rolling(7).mean().reset_index(level=0, drop=True)
    df["rolling_mean_14"] = shifted_sales.groupby(df["plu_code"]).rolling(14).mean().reset_index(level=0, drop=True)
    df["rolling_mean_28"] = shifted_sales.groupby(df["plu_code"]).rolling(28).mean().reset_index(level=0, drop=True)

    # 6) target = next day sales of same product
    df["target_sales"] = grp["sales_qty"].shift(-1)

    # 8) drop NaNs created by lag/rolling/target
    feature_cols = [
        "sales_lag_1",
        "sales_lag_7",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_28",
        "target_sales",
    ]
    before_drop = len(df)
    model_df = df.dropna(subset=feature_cols).copy()
    dropped_rows = before_drop - len(model_df)

    # save
    save_df = model_df.copy()
    save_df["date"] = save_df["date"].dt.strftime("%Y-%m-%d")
    save_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 10/11) report
    lines: list[str] = []
    lines.append("Model Features Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"initial_rows: {before_drop}")
    lines.append(f"final_rows: {len(model_df)}")
    lines.append(f"rows_dropped_by_nan_filters: {dropped_rows}")
    lines.append(f"date_min: {model_df['date'].min()}")
    lines.append(f"date_max: {model_df['date'].max()}")
    lines.append(f"plu_code_unique_count: {model_df['plu_code'].nunique()}")
    lines.append("")
    lines.append("[target_sales stats]")
    lines.append(f"min: {model_df['target_sales'].min()}")
    lines.append(f"max: {model_df['target_sales'].max()}")
    lines.append(f"mean: {model_df['target_sales'].mean()}")
    lines.append(f"median: {model_df['target_sales'].median()}")
    lines.append("")
    lines.append("[Missing Count]")
    missing_counts = model_df.isna().sum()
    for col, cnt in missing_counts.items():
        lines.append(f"{col}: {int(cnt)}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved model features: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Final rows: {len(model_df)}")
    print(f"Date range: {model_df['date'].min()} ~ {model_df['date'].max()}")
    print(f"PLU unique: {model_df['plu_code'].nunique()}")


if __name__ == "__main__":
    main()
