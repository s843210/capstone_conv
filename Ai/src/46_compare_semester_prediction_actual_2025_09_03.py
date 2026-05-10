from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_semester_binary.csv"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_semester_binary_model.pkl"

TARGET_DATE = pd.Timestamp("2025-09-03")

OUT_CSV = BASE_DIR / "outputs" / "reports" / "semester_prediction_vs_actual_2025_09_03.csv"
OUT_SUMMARY = BASE_DIR / "outputs" / "reports" / "semester_prediction_vs_actual_2025_09_03_summary.txt"


def encode_with_mapping(values: pd.Series, mapping: dict[str, int]) -> pd.Series:
    return values.astype(str).fillna("").map(mapping).fillna(-1).astype(int)


def fmt_metric(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.6f}"


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    compare_df = df[df["date"] == TARGET_DATE].copy()

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    feature_cols = bundle.get("feature_cols", [])
    categorical_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    required_out_cols = [
        "date",
        "plu_code",
        "product_name",
        "product_category",
        "target_sales",
        "prediction",
        "abs_error",
    ]

    if compare_df.empty:
        out_df = pd.DataFrame(columns=required_out_cols)
        out_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

        lines: list[str] = []
        lines.append("Semester Prediction vs Actual Summary")
        lines.append(f"compare_date: {TARGET_DATE.strftime('%Y-%m-%d')}")
        lines.append("item_count: 0")
        lines.append("actual_sales_sum: 0")
        lines.append("predicted_sales_sum: 0")
        lines.append("MAE: N/A")
        lines.append("RMSE: N/A")
        lines.append("R2: N/A")
        lines.append("abs_error_mean: N/A")
        lines.append("abs_error_median: N/A")
        lines.append("abs_error_max: N/A")
        lines.append("note: No rows found for the target date in input dataset.")
        OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

        print(f"Saved empty comparison csv: {OUT_CSV}")
        print(f"Saved summary report: {OUT_SUMMARY}")
        print("No rows found for target date.")
        return

    X = compare_df[feature_cols].copy()

    for c in categorical_cols:
        mapping = label_maps.get(c, {})
        X[c] = encode_with_mapping(X[c], mapping)

    for c in X.columns:
        if c not in categorical_cols:
            X[c] = pd.to_numeric(X[c], errors="coerce")

    X = X.fillna(0)

    preds = model.predict(X)

    y_true = pd.to_numeric(compare_df["target_sales"], errors="coerce")
    valid = y_true.notna()

    out_df = compare_df.copy()
    out_df["prediction"] = preds
    out_df["target_sales"] = y_true
    out_df = out_df[valid].copy()
    out_df["abs_error"] = (out_df["target_sales"] - out_df["prediction"]).abs()

    out_df = out_df.sort_values("abs_error", ascending=False)

    save_df = out_df.copy()
    save_df["date"] = pd.to_datetime(save_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    save_df = save_df[required_out_cols]
    save_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    y = out_df["target_sales"]
    p = out_df["prediction"]

    mae = float(mean_absolute_error(y, p)) if len(out_df) > 0 else None
    rmse = float(np.sqrt(mean_squared_error(y, p))) if len(out_df) > 0 else None
    r2 = float(r2_score(y, p)) if len(out_df) > 1 else None

    actual_sum = float(y.sum()) if len(out_df) > 0 else 0.0
    pred_sum = float(p.sum()) if len(out_df) > 0 else 0.0

    abs_mean = float(out_df["abs_error"].mean()) if len(out_df) > 0 else None
    abs_median = float(out_df["abs_error"].median()) if len(out_df) > 0 else None
    abs_max = float(out_df["abs_error"].max()) if len(out_df) > 0 else None

    lines: list[str] = []
    lines.append("Semester Prediction vs Actual Summary")
    lines.append(f"compare_date: {TARGET_DATE.strftime('%Y-%m-%d')}")
    lines.append(f"item_count: {len(out_df)}")
    lines.append(f"actual_sales_sum: {actual_sum}")
    lines.append(f"predicted_sales_sum: {pred_sum}")
    lines.append(f"MAE: {fmt_metric(mae)}")
    lines.append(f"RMSE: {fmt_metric(rmse)}")
    lines.append(f"R2: {fmt_metric(r2)}")
    lines.append(f"abs_error_mean: {fmt_metric(abs_mean)}")
    lines.append(f"abs_error_median: {fmt_metric(abs_median)}")
    lines.append(f"abs_error_max: {fmt_metric(abs_max)}")

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved comparison csv: {OUT_CSV}")
    print(f"Saved summary report: {OUT_SUMMARY}")
    print(f"Rows compared: {len(out_df)}")


if __name__ == "__main__":
    main()
