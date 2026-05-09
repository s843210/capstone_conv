"""Inference preprocessing for serving (FastAPI / interactive).

Provides a reusable ``ModelPredictor`` class that can be imported by a
FastAPI app *or* used standalone for interactive testing.

Based on legacy 32_interactive_prediction_test.
"""

from __future__ import annotations

import os
from math import ceil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ..config import Paths, Inference
from ..utils.encoding import encode_with_mapping


class ModelPredictor:
    """Wraps a trained model bundle for inference."""

    def __init__(self, model_path: Path | str | None = None) -> None:
        model_path = Path(
            model_path
            or os.environ.get("MODEL_PATH", "")
            or str(Paths.MODEL_RF_FAST)
        )
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.feature_cols: list[str] = bundle["feature_cols"]
        self.categorical_cols: list[str] = bundle.get("categorical_cols", [])
        self.label_maps: dict[str, dict[str, int]] = bundle.get("label_maps", {})

    def predict_one(
        self,
        features: dict[str, object],
        safety_factor: float | None = None,
    ) -> dict[str, object]:
        """Predict for a single item given its feature dict."""
        safety_factor = safety_factor or Inference.SAFETY_FACTOR
        row = {c: features.get(c, 0) for c in self.feature_cols}

        # Apply label encoding
        for c in self.categorical_cols:
            mapping = self.label_maps.get(c, {})
            val = str(row.get(c, ""))
            row[c] = mapping.get(val, -1)

        X = pd.DataFrame([row])[self.feature_cols]
        for c in X.columns:
            if c not in self.categorical_cols:
                X[c] = pd.to_numeric(X[c], errors="coerce")
        X = X.fillna(0)

        pred = float(self.model.predict(X)[0])
        predicted_qty = max(pred, 0.0)
        recommended = int(ceil(predicted_qty * safety_factor)) if predicted_qty > 0 else 0

        return {
            "predicted_sales_qty": round(predicted_qty, 4),
            "recommended_order_qty": recommended,
        }

    def predict_batch(
        self,
        items: list[dict[str, object]],
        safety_factor: float | None = None,
    ) -> list[dict[str, object]]:
        """Predict for multiple items."""
        return [self.predict_one(item, safety_factor) for item in items]


# ===================================================================
# Interactive CLI  (direct execution)
# ===================================================================

def interactive_test() -> None:
    """Interactive CLI test — search by product name or plu_code."""
    data_path = Paths.MODEL_FEATURES
    if not data_path.exists():
        raise FileNotFoundError(f"Data not found: {data_path}")

    predictor = ModelPredictor()

    df = pd.read_csv(data_path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    if "product_name" in df.columns:
        df["product_name"] = df["product_name"].astype(str).str.strip()

    user_input = input("상품명 또는 plu_code를 입력하세요: ").strip()
    if not user_input:
        print("입력이 비어 있습니다.")
        return

    by_plu = df["plu_code"] == user_input
    by_name = (
        df["product_name"].str.contains(user_input, case=False, na=False)
        if "product_name" in df.columns
        else False
    )
    matched = df[by_plu | by_name]

    if matched.empty:
        print("일치하는 상품을 찾지 못했습니다.")
        return

    latest = matched.sort_values("date").tail(1).iloc[0]
    features = {c: latest[c] for c in predictor.feature_cols if c in latest.index}
    result = predictor.predict_one(features)

    print("\n[예측 결과]")
    print(f"상품명: {latest.get('product_name', '')}")
    print(f"plu_code: {latest.get('plu_code', '')}")
    print(f"기준일: {latest['date'].strftime('%Y-%m-%d')}")
    print(f"예측 판매량: {result['predicted_sales_qty']}")
    print(f"추천 발주량: {result['recommended_order_qty']}")


if __name__ == "__main__":
    interactive_test()
