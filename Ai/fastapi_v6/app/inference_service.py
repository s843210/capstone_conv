from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .feature_builder import FeatureRow
from .model_loader import ModelBundle
from .order_policy import calc_recommended_order


@dataclass
class PredictionRow:
    plu_code: str
    product_name: str
    category_m_name: str
    predicted_sales: int
    recommended_order: int
    confidence_score: float
    ai_message: str


def _confidence_from_trees(bundle: ModelBundle, X: np.ndarray) -> np.ndarray:
    if not hasattr(bundle.model, "estimators_"):
        return np.full(X.shape[0], 0.5)

    tree_preds_log = np.array([tree.predict(X) for tree in bundle.model.estimators_])
    tree_preds_raw = np.expm1(tree_preds_log)
    pred_std = np.std(tree_preds_raw, axis=0)
    pred_mean = np.mean(tree_preds_raw, axis=0)
    return np.clip(1 - (pred_std / (pred_mean + 1.0)), 0, 1)


def run_inference(bundle: ModelBundle, rows: list[FeatureRow]) -> list[PredictionRow]:
    if not rows:
        return []

    X = np.array([[r.model_features[col] for col in bundle.feature_cols] for r in rows], dtype=float)

    pred_log = bundle.model.predict(X)
    pred_raw = np.expm1(pred_log)
    pred_int = np.maximum(0, np.round(pred_raw)).astype(int)
    confidences = _confidence_from_trees(bundle, X)

    out: list[PredictionRow] = []
    for idx, row in enumerate(rows):
        predicted_sales = int(pred_int[idx])
        recommended_order = calc_recommended_order(
            predicted_sales=predicted_sales,
            safety_stock=row.safety_stock,
            current_stock=row.current_stock,
        )
        confidence = float(round(float(confidences[idx]), 4))

        out.append(
            PredictionRow(
                plu_code=row.plu_code,
                product_name=row.product_name,
                category_m_name=row.category_m_name,
                predicted_sales=predicted_sales,
                recommended_order=recommended_order,
                confidence_score=confidence,
                ai_message="",
            )
        )

    return out
