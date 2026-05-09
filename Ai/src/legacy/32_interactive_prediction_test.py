from __future__ import annotations

from math import ceil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_fast_model.pkl"
DATA_PATH = BASE_DIR / "data" / "processed" / "model_features.csv"
SAFETY_FACTOR = 1.2


def encode_with_mapping(values: pd.Series, mapping: dict[str, int]) -> pd.Series:
    return values.astype(str).fillna("").map(mapping).fillna(-1).astype(int)


def main() -> None:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_PATH}")

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    categorical_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    df = pd.read_csv(DATA_PATH, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    if "product_name" in df.columns:
        df["product_name"] = df["product_name"].astype(str).str.strip()

    user_input = input("상품명 또는 plu_code를 입력하세요: ").strip()
    if not user_input:
        print("입력이 비어 있습니다.")
        return

    # plu_code 정확 일치 또는 product_name 부분 일치
    by_plu = df["plu_code"] == user_input
    by_name = df["product_name"].str.contains(user_input, case=False, na=False) if "product_name" in df.columns else False
    matched = df[by_plu | by_name].copy()

    if matched.empty:
        print("일치하는 상품을 찾지 못했습니다.")
        return

    latest = matched.sort_values("date").tail(1).copy()
    row = latest.iloc[0]

    X = latest[feature_cols].copy()
    for c in categorical_cols:
        mapping = label_maps.get(c, {})
        X[c] = encode_with_mapping(X[c], mapping)
    for c in X.columns:
        if c not in categorical_cols:
            X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.fillna(0)

    pred = float(model.predict(X)[0])
    predicted_sales_qty = max(pred, 0.0)
    recommended_order_qty = int(ceil(predicted_sales_qty * SAFETY_FACTOR)) if predicted_sales_qty > 0 else 0

    recent_sales = float(row["sales_qty"]) if "sales_qty" in row.index else np.nan

    print("\n[예측 결과]")
    print(f"상품명: {row.get('product_name', '')}")
    print(f"plu_code: {row.get('plu_code', '')}")
    print(f"기준일: {row['date'].strftime('%Y-%m-%d')}")
    print(f"최근 판매량(sales_qty): {recent_sales}")
    print(f"예측 판매량(predicted_sales_qty): {predicted_sales_qty:.4f}")
    print(f"추천 발주량(recommended_order_qty): {recommended_order_qty}")


if __name__ == "__main__":
    main()
