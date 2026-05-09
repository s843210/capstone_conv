from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features.csv"

OUT_JSON = BASE_DIR / "outputs" / "reports" / "baseline_result.json"
OUT_CAT_CSV = BASE_DIR / "outputs" / "reports" / "baseline_category_mae.csv"
OUT_SAMPLE_CSV = BASE_DIR / "outputs" / "reports" / "baseline_predictions_sample.csv"


def mae(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def r2(y_true: pd.Series, y_pred: pd.Series) -> float:
    y_bar = float(np.mean(y_true))
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_bar) ** 2))
    if ss_tot == 0:
        return 0.0
    return float(1 - (ss_res / ss_tot))


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    required = {"date", "target_sales", "rolling_mean_7", "product_category"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["target_sales"] = pd.to_numeric(df["target_sales"], errors="coerce")
    df["baseline_pred"] = pd.to_numeric(df["rolling_mean_7"], errors="coerce")
    df = df[df["date"].notna() & df["target_sales"].notna() & df["baseline_pred"].notna()].copy()

    train_start = pd.Timestamp("2024-04-02")
    train_end = pd.Timestamp("2025-12-31")
    test_start = pd.Timestamp("2026-01-01")

    train_df = df[(df["date"] >= train_start) & (df["date"] <= train_end)].copy()
    test_df = df[df["date"] >= test_start].copy()

    if test_df.empty:
        raise ValueError("Test split is empty. Check date range in model_features.csv")

    y_true = test_df["target_sales"]
    y_pred = test_df["baseline_pred"]

    overall_mae = mae(y_true, y_pred)
    overall_rmse = rmse(y_true, y_pred)
    overall_r2 = r2(y_true, y_pred)

    cat_mae = (
        test_df.groupby("product_category", as_index=False)
        .apply(lambda g: pd.Series({"mae": mae(g["target_sales"], g["baseline_pred"]), "count": len(g)}))
        .reset_index(drop=True)
        .sort_values("mae")
    )
    cat_mae.to_csv(OUT_CAT_CSV, index=False, encoding="utf-8-sig")

    sample_cols = [
        "date",
        "plu_code",
        "product_name",
        "product_category",
        "target_sales",
        "baseline_pred",
    ]
    sample_cols = [c for c in sample_cols if c in test_df.columns]
    sample_df = test_df[sample_cols].sort_values(["date", "plu_code"]).head(500)
    sample_df.to_csv(OUT_SAMPLE_CSV, index=False, encoding="utf-8-sig")

    result = {
        "model": "baseline_rolling_mean_7",
        "split": {
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_start": str(test_start.date()),
        },
        "rows": {
            "total_after_clean": int(len(df)),
            "train": int(len(train_df)),
            "test": int(len(test_df)),
        },
        "metrics_test": {
            "mae": overall_mae,
            "rmse": overall_rmse,
            "r2": overall_r2,
        },
    }

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved result json: {OUT_JSON}")
    print(f"Saved category mae: {OUT_CAT_CSV}")
    print(f"Saved sample predictions: {OUT_SAMPLE_CSV}")
    print(f"Test MAE: {overall_mae:.6f}")
    print(f"Test RMSE: {overall_rmse:.6f}")
    print(f"Test R2: {overall_r2:.6f}")


if __name__ == "__main__":
    main()
