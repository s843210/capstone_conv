from __future__ import annotations

from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PRED_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction.csv"
FEATURE_CSV = BASE_DIR / "data" / "processed" / "model_features.csv"

OUT_CSV = BASE_DIR / "outputs" / "reports" / "order_recommendation_guardrailed.csv"
OUT_REPORT = BASE_DIR / "outputs" / "reports" / "order_recommendation_guardrailed_summary.txt"

# Guardrail params
SAFETY_FACTOR = 1.05
BLEND_ALPHA = 0.4  # final_pred = alpha*model_pred + (1-alpha)*recent7_mean
UPPER_CAP_MULTIPLIER = 1.2  # final_pred <= recent7_mean * multiplier
LOWER_FLOOR = 0.0


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    if not PRED_CSV.exists():
        raise FileNotFoundError(f"Prediction file not found: {PRED_CSV}")
    if not FEATURE_CSV.exists():
        raise FileNotFoundError(f"Feature file not found: {FEATURE_CSV}")

    pred = pd.read_csv(PRED_CSV, low_memory=False)
    feat = pd.read_csv(FEATURE_CSV, low_memory=False)

    required_pred = {"plu_code", "product_name", "product_category", "predicted_sales_qty", "base_date", "predict_date"}
    missing = required_pred - set(pred.columns)
    if missing:
        raise KeyError(f"Missing prediction columns: {sorted(missing)}")

    if "rolling_mean_7" not in feat.columns:
        raise KeyError("'rolling_mean_7' not found in model_features.csv")

    pred["plu_code"] = pred["plu_code"].astype(str).str.strip()
    pred["predicted_sales_qty"] = pd.to_numeric(pred["predicted_sales_qty"], errors="coerce").fillna(0.0)

    feat["plu_code"] = feat["plu_code"].astype(str).str.strip()
    feat["rolling_mean_7"] = pd.to_numeric(feat["rolling_mean_7"], errors="coerce")
    recent7 = (
        feat.sort_values(["plu_code", "date"])
        .groupby("plu_code", as_index=False)
        .tail(1)[["plu_code", "rolling_mean_7"]]
        .rename(columns={"rolling_mean_7": "recent7_mean"})
    )

    merged = pred.merge(recent7, on="plu_code", how="left")
    merged["recent7_mean"] = pd.to_numeric(merged["recent7_mean"], errors="coerce").fillna(0.0)

    # Blend + cap guardrail
    merged["blended_pred"] = (
        BLEND_ALPHA * merged["predicted_sales_qty"] + (1.0 - BLEND_ALPHA) * merged["recent7_mean"]
    )
    cap = merged["recent7_mean"] * UPPER_CAP_MULTIPLIER
    merged["guardrailed_predicted_sales_qty"] = np.minimum(merged["blended_pred"], cap)
    merged["guardrailed_predicted_sales_qty"] = np.maximum(merged["guardrailed_predicted_sales_qty"], LOWER_FLOOR)

    # Order qty
    merged["recommended_order_qty"] = merged["guardrailed_predicted_sales_qty"].map(
        lambda x: 0 if x <= 0 else int(ceil(float(x) * SAFETY_FACTOR))
    )
    merged["recommended_order_qty"] = merged["recommended_order_qty"].astype(int)

    out = merged[
        [
            "base_date",
            "predict_date",
            "plu_code",
            "product_name",
            "product_category",
            "predicted_sales_qty",
            "recent7_mean",
            "guardrailed_predicted_sales_qty",
            "recommended_order_qty",
        ]
    ].copy()
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    changed_count = int((out["guardrailed_predicted_sales_qty"] != out["predicted_sales_qty"]).sum())
    total = len(out)
    total_order = int(out["recommended_order_qty"].sum())
    mean_order = float(out["recommended_order_qty"].mean()) if total else 0.0

    top20 = out.sort_values("recommended_order_qty", ascending=False).head(20)

    lines: list[str] = []
    lines.append("Order Recommendation Guardrailed Summary")
    lines.append(f"input_prediction_csv: {PRED_CSV.as_posix()}")
    lines.append(f"input_feature_csv: {FEATURE_CSV.as_posix()}")
    lines.append(f"output_csv: {OUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"safety_factor: {SAFETY_FACTOR}")
    lines.append(f"blend_alpha: {BLEND_ALPHA}")
    lines.append(f"upper_cap_multiplier: {UPPER_CAP_MULTIPLIER}")
    lines.append("")
    lines.append(f"total_products: {total}")
    lines.append(f"changed_by_guardrail_count: {changed_count}")
    lines.append(f"total_recommended_order_qty: {total_order}")
    lines.append(f"average_recommended_order_qty: {mean_order}")
    lines.append("")
    lines.append("[Top 20 Recommended Order Qty]")
    if top20.empty:
        lines.append("None")
    else:
        lines.append(
            top20[
                [
                    "plu_code",
                    "product_name",
                    "product_category",
                    "predicted_sales_qty",
                    "recent7_mean",
                    "guardrailed_predicted_sales_qty",
                    "recommended_order_qty",
                ]
            ].to_string(index=False)
        )

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved guardrailed recommendation: {OUT_CSV}")
    print(f"Saved summary: {OUT_REPORT}")
    print(f"Products: {total}")
    print(f"Changed by guardrail: {changed_count}")
    print(f"Total recommended qty: {total_order}")


if __name__ == "__main__":
    main()
