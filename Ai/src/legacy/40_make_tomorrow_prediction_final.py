from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_weather_binary.csv"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_weather_binary_model.pkl"
OUTPUT_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction_final.csv"


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

    if "plu_code" not in df.columns:
        raise KeyError("'plu_code' column not found in model_features_weather_binary.csv")

    # 1) latest base_date row per plu_code
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    latest_idx = (
        df.sort_values(["plu_code", "date"])  # ascending
        .groupby("plu_code", as_index=False)
        .tail(1)
        .index
    )
    latest_df = df.loc[latest_idx].copy().sort_values(["date", "plu_code"]).reset_index(drop=True)

    # 3) use model bundle metadata from training
    X = latest_df[feature_cols].copy()

    for col in categorical_cols:
        mapping = label_maps.get(col, {})
        values = X[col].astype(str).fillna("")
        X[col] = values.map(mapping).fillna(-1).astype(int)

    for col in X.columns:
        if col not in categorical_cols:
            X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)

    preds = model.predict(X)

    # 4) clip negative predictions to zero
    preds = np.where(preds < 0, 0, preds)

    # 2) predict_date = base_date + 1 day
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

    # 5) output columns in required order
    out = out[
        [
            "base_date",
            "predict_date",
            "plu_code",
            "product_name",
            "product_category",
            "predicted_sales_qty",
        ]
    ]

    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"Saved prediction file: {OUTPUT_CSV}")
    print(f"Rows: {len(out)}")
    print(f"Base date min/max: {out['base_date'].min()} ~ {out['base_date'].max()}")


if __name__ == "__main__":
    main()
