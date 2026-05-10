"""Infer — tomorrow prediction, order recommendation, guardrails, API spec.

Consolidates logic from legacy scripts 29, 30, 33, 40, 41, 42.
"""

from __future__ import annotations

import json
from math import ceil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ..config import Paths, Inference
from ..utils.io import safe_read_csv, safe_save_csv, ensure_dir
from ..utils.encoding import encode_with_mapping
from ..utils.report import write_report


# ===================================================================
# Tomorrow prediction  (legacy 29)
# ===================================================================

def predict_tomorrow(
    input_csv: Path | None = None,
    model_path: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Load the trained model and predict next-day sales for each product."""
    input_csv = input_csv or Paths.MODEL_FEATURES_WEATHER_BINARY
    model_path = model_path or Paths.MODEL_RF_FAST
    output_csv = output_csv or (Paths.REPORTS_DIR / "tomorrow_sales_prediction.csv")

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    df = safe_read_csv(input_csv)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    bundle = joblib.load(model_path)
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    cat_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    latest_idx = df.sort_values(["plu_code", "date"]).groupby("plu_code", as_index=False).tail(1).index
    latest = df.loc[latest_idx].copy().sort_values(["date", "plu_code"]).reset_index(drop=True)

    X = latest[feature_cols].copy()
    for c in cat_cols:
        X[c] = encode_with_mapping(X[c], label_maps.get(c, {}))
    for c in X.columns:
        if c not in cat_cols:
            X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.fillna(0)

    preds = model.predict(X)
    preds = np.where(preds < 0, 0, preds)

    out = pd.DataFrame({
        "base_date": latest["date"].dt.strftime("%Y-%m-%d"),
        "predict_date": (latest["date"] + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d"),
        "plu_code": latest["plu_code"],
        "product_name": latest.get("product_name", ""),
        "product_category": latest.get("product_category", ""),
        "predicted_sales_qty": preds,
    })

    safe_save_csv(out, output_csv)
    print(f"Prediction: {len(out)} products → {output_csv.name}")
    return out


# ===================================================================
# Order recommendation  (legacy 30)
# ===================================================================

def recommend_orders(
    pred_csv: Path | None = None,
    output_csv: Path | None = None,
    safety_factor: float | None = None,
) -> pd.DataFrame:
    """Compute recommended order quantities from predictions."""
    pred_csv = pred_csv or (Paths.REPORTS_DIR / "tomorrow_sales_prediction.csv")
    output_csv = output_csv or (Paths.REPORTS_DIR / "order_recommendation.csv")
    safety_factor = safety_factor or Inference.SAFETY_FACTOR

    df = safe_read_csv(pred_csv)
    df["predicted_sales_qty"] = pd.to_numeric(df["predicted_sales_qty"], errors="coerce").fillna(0)
    df["recommended_order_qty"] = df["predicted_sales_qty"].map(
        lambda x: 0 if x <= 0 else int(ceil(float(x) * safety_factor))
    )

    out_cols = [
        "base_date", "predict_date", "plu_code", "product_name",
        "product_category", "predicted_sales_qty", "recommended_order_qty",
    ]
    out = df[[c for c in out_cols if c in df.columns]].copy()
    safe_save_csv(out, output_csv)

    total = int(out["recommended_order_qty"].sum())
    print(f"Orders: {len(out)} products, total qty {total} → {output_csv.name}")
    return out


# ===================================================================
# Guardrails  (legacy 33)
# ===================================================================

def apply_guardrails(
    pred_csv: Path | None = None,
    feature_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Apply blending + capping guardrails to predictions."""
    pred_csv = pred_csv or (Paths.REPORTS_DIR / "tomorrow_sales_prediction.csv")
    feature_csv = feature_csv or Paths.MODEL_FEATURES_WEATHER_BINARY
    output_csv = output_csv or (Paths.REPORTS_DIR / "order_recommendation_guardrailed.csv")

    sf = Inference.GUARDRAIL_SAFETY_FACTOR
    alpha = Inference.GUARDRAIL_BLEND_ALPHA
    cap_mult = Inference.GUARDRAIL_UPPER_CAP
    floor = Inference.GUARDRAIL_LOWER_FLOOR

    pred = safe_read_csv(pred_csv)
    feat = safe_read_csv(feature_csv)

    pred["plu_code"] = pred["plu_code"].astype(str).str.strip()
    pred["predicted_sales_qty"] = pd.to_numeric(pred["predicted_sales_qty"], errors="coerce").fillna(0)

    feat["plu_code"] = feat["plu_code"].astype(str).str.strip()
    feat["rolling_mean_7"] = pd.to_numeric(feat["rolling_mean_7"], errors="coerce")

    recent7 = (
        feat.sort_values(["plu_code", "date"])
        .groupby("plu_code", as_index=False).tail(1)[["plu_code", "rolling_mean_7"]]
        .rename(columns={"rolling_mean_7": "recent7_mean"})
    )

    merged = pred.merge(recent7, on="plu_code", how="left")
    merged["recent7_mean"] = pd.to_numeric(merged["recent7_mean"], errors="coerce").fillna(0)

    # Blend + cap
    merged["blended"] = alpha * merged["predicted_sales_qty"] + (1 - alpha) * merged["recent7_mean"]
    cap = merged["recent7_mean"] * cap_mult
    merged["guardrailed_predicted_sales_qty"] = np.minimum(merged["blended"], cap)
    merged["guardrailed_predicted_sales_qty"] = np.maximum(merged["guardrailed_predicted_sales_qty"], floor)

    merged["recommended_order_qty"] = merged["guardrailed_predicted_sales_qty"].map(
        lambda x: 0 if x <= 0 else int(ceil(float(x) * sf))
    ).astype(int)

    out_cols = [
        "base_date", "predict_date", "plu_code", "product_name",
        "product_category", "predicted_sales_qty", "recent7_mean",
        "guardrailed_predicted_sales_qty", "recommended_order_qty",
    ]
    out = merged[[c for c in out_cols if c in merged.columns]].copy()
    safe_save_csv(out, output_csv)

    print(f"Guardrailed: {len(out)} products → {output_csv.name}")
    return out


# ===================================================================
# API Spec  (legacy 42)
# ===================================================================

FEATURE_DESCRIPTIONS = {
    "plu_code": "Product PLU code (string, label-encoded at inference).",
    "product_category": "Product category (string, label-encoded at inference).",
    "sales_qty": "Current observed sales quantity.",
    "purchase_qty": "Current observed purchase quantity.",
    "is_start_semester": "Start-of-semester flag (0/1).",
    "is_end_semester": "End-of-semester flag (0/1).",
    "is_exam": "Exam period flag (0/1).",
    "is_vacation": "Vacation period flag (0/1).",
    "is_festival": "Festival/event flag (0/1).",
    "is_holiday_or_no_class": "Holiday or no-class flag (0/1).",
    "class_count": "Class count for the date weekday.",
    "monday_class_count": "Monday class count.",
    "tuesday_class_count": "Tuesday class count.",
    "wednesday_class_count": "Wednesday class count.",
    "thursday_class_count": "Thursday class count.",
    "friday_class_count": "Friday class count.",
    "is_rainy": "Binary weather feature: 1 if rainfall > 0 else 0.",
    "is_hot": "Binary weather feature: 1 if avg_temp >= 27 else 0.",
    "is_cold": "Binary weather feature: 1 if avg_temp <= 5 else 0.",
    "year": "Year extracted from date.",
    "month": "Month extracted from date.",
    "day": "Day extracted from date.",
    "weekday": "Weekday index (Mon=0 ... Sun=6).",
    "is_weekend": "Weekend flag (0/1).",
    "sales_lag_1": "Previous sales quantity for same plu_code.",
    "sales_lag_7": "Sales quantity 7 steps before for same plu_code.",
    "rolling_mean_7": "Rolling mean over previous 7 points (after shift(1)).",
    "rolling_mean_14": "Rolling mean over previous 14 points (after shift(1)).",
    "rolling_mean_28": "Rolling mean over previous 28 points (after shift(1)).",
}


def build_api_spec(
    model_path: Path | None = None,
    output_md: Path | None = None,
) -> Path:
    """Generate a markdown API specification from the trained model bundle."""
    model_path = model_path or Paths.MODEL_RF_FAST
    output_md = output_md or (Paths.REPORTS_DIR / "model_api_spec.md")

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    bundle = joblib.load(model_path)
    feature_cols = bundle.get("feature_cols", [])
    cat_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    lines: list[str] = []
    lines.append("# Model API Spec (RandomForest + Binary Weather)")
    lines.append("")
    lines.append("## 1. Model File")
    lines.append(f"- Path: `{model_path.relative_to(model_path.parents[2])}`")
    lines.append("- Bundle keys: `model`, `feature_cols`, `categorical_cols`, `label_maps`")
    lines.append("")

    lines.append("## 2. Input Features")
    lines.append("| feature | type | description |")
    lines.append("|---|---|---|")
    for c in feature_cols:
        t = "string" if c in cat_cols else "number"
        desc = FEATURE_DESCRIPTIONS.get(c, "Model input feature")
        lines.append(f"| `{c}` | `{t}` | {desc} |")
    lines.append("")

    lines.append("## 3. Categorical Encoding")
    lines.append("- `plu_code`, `product_category` are LabelEncoded.")
    lines.append("- Use `label_maps` inside model bundle for consistent encoding.")
    lines.append("- Unknown category values should map to `-1`.")
    for c in cat_cols:
        lines.append(f"- `{c}` classes: {len(label_maps.get(c, {}))}")
    lines.append("")

    lines.append("## 4. Binary Weather Features")
    lines.append("- `is_rainy`: 1 if rainfall > 0 else 0")
    lines.append("- `is_hot`: 1 if avg_temp >= 27 else 0")
    lines.append("- `is_cold`: 1 if avg_temp <= 5 else 0")
    lines.append("")

    lines.append("## 5. Order Recommendation Formula")
    lines.append(f"- `recommended_order_qty = ceil(predicted_sales_qty * {Inference.SAFETY_FACTOR})`")

    ensure_dir(output_md)
    output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"API spec: {output_md.name}")
    return output_md
