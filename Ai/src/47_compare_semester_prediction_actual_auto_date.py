from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_semester_binary.csv"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_semester_binary_model.pkl"

REQUEST_DATE = pd.Timestamp("2025-09-03")
PRIMARY_START = pd.Timestamp("2025-09-01")
PRIMARY_END = pd.Timestamp("2025-09-10")
SEPT_START = pd.Timestamp("2025-09-01")
SEPT_END = pd.Timestamp("2025-09-30")

OUT_CSV = BASE_DIR / "outputs" / "reports" / "semester_prediction_vs_actual_auto_date.csv"
OUT_SUMMARY = BASE_DIR / "outputs" / "reports" / "semester_prediction_vs_actual_auto_date_summary.txt"


def encode_with_mapping(values: pd.Series, mapping: dict[str, int]) -> pd.Series:
    return values.astype(str).fillna("").map(mapping).fillna(-1).astype(int)


def fmt_metric(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.6f}"


def choose_date(unique_dates: pd.Series) -> tuple[pd.Timestamp, str]:
    primary = unique_dates[(unique_dates >= PRIMARY_START) & (unique_dates <= PRIMARY_END)]
    if not primary.empty:
        return primary.min(), "range_2025_09_01_to_2025_09_10"

    sept = unique_dates[(unique_dates >= SEPT_START) & (unique_dates <= SEPT_END)]
    if not sept.empty:
        return sept.min(), "range_2025_09"

    diffs = (unique_dates - REQUEST_DATE).abs()
    idx = diffs.idxmin()
    return unique_dates.loc[idx], "nearest_overall"


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()
    if df.empty:
        raise ValueError("Input dataset has no valid date rows.")

    unique_dates = pd.Series(sorted(df["date"].dropna().unique()))
    selected_date, selected_rule = choose_date(unique_dates)

    compare_df = df[df["date"] == selected_date].copy()

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    feature_cols = bundle.get("feature_cols", [])
    categorical_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    X = compare_df[feature_cols].copy()
    for c in categorical_cols:
        mapping = label_maps.get(c, {})
        X[c] = encode_with_mapping(X[c], mapping)
    for c in X.columns:
        if c not in categorical_cols:
            X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.fillna(0)

    preds = model.predict(X)

    out_df = compare_df.copy()
    out_df["target_sales"] = pd.to_numeric(out_df["target_sales"], errors="coerce")
    out_df["prediction"] = preds
    out_df = out_df[out_df["target_sales"].notna()].copy()
    out_df["abs_error"] = (out_df["target_sales"] - out_df["prediction"]).abs()
    out_df = out_df.sort_values("abs_error", ascending=False)

    save_df = out_df.copy()
    save_df["date"] = save_df["date"].dt.strftime("%Y-%m-%d")
    save_df = save_df[
        [
            "date",
            "plu_code",
            "product_name",
            "product_category",
            "target_sales",
            "prediction",
            "abs_error",
        ]
    ]
    save_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    y = out_df["target_sales"]
    p = out_df["prediction"]

    mae = float(mean_absolute_error(y, p)) if len(out_df) > 0 else None
    rmse = float(np.sqrt(mean_squared_error(y, p))) if len(out_df) > 0 else None
    r2 = float(r2_score(y, p)) if len(out_df) > 1 else None

    actual_sum = float(y.sum()) if len(out_df) > 0 else 0.0
    pred_sum = float(p.sum()) if len(out_df) > 0 else 0.0

    lines: list[str] = []
    lines.append("Semester Prediction vs Actual (Auto Date) Summary")
    lines.append(f"requested_date: {REQUEST_DATE.strftime('%Y-%m-%d')}")
    lines.append(f"selected_date: {selected_date.strftime('%Y-%m-%d')}")
    lines.append(f"selection_rule: {selected_rule}")
    lines.append(f"item_count: {len(out_df)}")
    lines.append(f"actual_sales_sum: {actual_sum}")
    lines.append(f"predicted_sales_sum: {pred_sum}")
    lines.append(f"MAE: {fmt_metric(mae)}")
    lines.append(f"RMSE: {fmt_metric(rmse)}")
    lines.append(f"R2: {fmt_metric(r2)}")

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    in_primary = unique_dates[(unique_dates >= PRIMARY_START) & (unique_dates <= PRIMARY_END)]
    print(
        "available_dates_2025_09_01_to_2025_09_10: "
        + (", ".join(pd.Series(in_primary).dt.strftime("%Y-%m-%d").tolist()) if len(in_primary) else "None")
    )
    print(f"Saved comparison csv: {OUT_CSV}")
    print(f"Saved summary report: {OUT_SUMMARY}")
    print(f"Selected date: {selected_date.strftime('%Y-%m-%d')} ({selected_rule})")
    print(f"Rows compared: {len(out_df)}")


if __name__ == "__main__":
    main()
