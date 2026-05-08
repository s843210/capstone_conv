from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features.csv"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_fast_model.pkl"
OUTPUT_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction.csv"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    categorical_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    # 4) latest row per product (plu_code)
    if "plu_code" not in df.columns:
        raise KeyError("'plu_code' column not found in model_features.csv")
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    latest_idx = df.sort_values(["plu_code", "date"]).groupby("plu_code", as_index=False).tail(1).index
    latest_df = df.loc[latest_idx].copy().sort_values(["date", "plu_code"]).reset_index(drop=True)

    # Build model input with the same feature order
    X = latest_df[feature_cols].copy()

    # Apply label encoding same as training
    for col in categorical_cols:
        mapping = label_maps.get(col, {})
        values = X[col].astype(str).fillna("")
        X[col] = values.map(mapping).fillna(-1).astype(int)

    # numeric conversion for all remaining columns
    for col in X.columns:
        if col not in categorical_cols:
            X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)

    preds = model.predict(X)
    preds = np.where(preds < 0, 0, preds)

    out = pd.DataFrame(
        {
            "base_date": latest_df["date"].dt.strftime("%Y-%m-%d"),
            "predict_date": (latest_df["date"] + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d"),
            "plu_code": latest_df["plu_code"],
            "product_name": latest_df["product_name"] if "product_name" in latest_df.columns else "",
            "product_category": latest_df["product_category"] if "product_category" in latest_df.columns else "",
            "predicted_sales_qty": preds,
        }
    )

    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"Saved prediction file: {OUTPUT_CSV}")
    print(f"Rows: {len(out)}")
    print(f"Base date min/max: {out['base_date'].min()} ~ {out['base_date'].max()}")


if __name__ == "__main__":
    main()
