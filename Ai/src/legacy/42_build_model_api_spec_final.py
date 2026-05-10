from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_weather_binary_model.pkl"
MODEL_FEATURES_CSV = BASE_DIR / "data" / "processed" / "model_features_weather_binary.csv"
PREDICTION_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction_final.csv"
ORDER_CSV = BASE_DIR / "outputs" / "reports" / "order_recommendation_final.csv"
OUT_MD = BASE_DIR / "outputs" / "reports" / "model_api_spec_final.md"

FINAL_METRICS = {
    "mae": 12.8477,
    "rmse": 24.1966,
    "r2": 0.6417,
}
OLD_METRICS = {
    "mae": 14.3009,
    "rmse": 26.2230,
    "r2": 0.5792,
}

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


def main() -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    for p in [MODEL_PATH, MODEL_FEATURES_CSV, PREDICTION_CSV, ORDER_CSV]:
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")

    bundle = joblib.load(MODEL_PATH)
    feature_cols = bundle.get("feature_cols", [])
    categorical_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    if not feature_cols:
        raise ValueError("feature_cols not found in model bundle")

    model_df = pd.read_csv(MODEL_FEATURES_CSV, low_memory=False)
    sample_row = model_df.iloc[0].copy()

    sample_features: dict[str, object] = {}
    for c in feature_cols:
        v = sample_row.get(c, 0)
        if c in categorical_cols:
            sample_features[c] = str(v)
        else:
            sample_features[c] = float(v) if pd.notna(v) else 0.0

    base_date_str = str(sample_row.get("date", "2026-02-01"))
    predict_date_str = (
        pd.to_datetime(base_date_str, errors="coerce") + pd.Timedelta(days=1)
    ).strftime("%Y-%m-%d")

    sample_request = {
        "base_date": base_date_str,
        "weather_input": {
            "rainfall": 1.2,
            "avg_temp": 28.1,
            "derived_binary": {
                "is_rainy": 1,
                "is_hot": 1,
                "is_cold": 0,
            },
        },
        "items": [
            {
                "plu_code": str(sample_row.get("plu_code", "8801056040925.0")),
                "product_name": "sample_product",
                "product_category": "sample_category",
                "features": sample_features,
            }
        ],
        "safety_factor": 1.2,
    }

    sample_response = {
        "base_date": base_date_str,
        "predict_date": predict_date_str,
        "results": [
            {
                "plu_code": str(sample_row.get("plu_code", "8801056040925.0")),
                "product_name": "sample_product",
                "product_category": "sample_category",
                "predicted_sales_qty": 18.42,
                "recommended_order_qty": 23,
            }
        ],
    }

    lines: list[str] = []
    lines.append("# Final Model API Spec (RandomForest + Binary Weather)")
    lines.append("")

    lines.append("## 1. Final Model File")
    lines.append("- Path: `outputs/models/random_forest_weather_binary_model.pkl`")
    lines.append("- Bundle keys: `model`, `feature_cols`, `categorical_cols`, `label_maps`")
    lines.append("")

    lines.append("## 2. Final Performance")
    lines.append(f"- MAE: {FINAL_METRICS['mae']}")
    lines.append(f"- RMSE: {FINAL_METRICS['rmse']}")
    lines.append(f"- R2: {FINAL_METRICS['r2']}")
    lines.append("")

    lines.append("## 3. Improvement vs Existing RF-fast")
    lines.append(f"- Existing RF-fast MAE: {OLD_METRICS['mae']} -> Final MAE: {FINAL_METRICS['mae']}")
    lines.append("- Binary weather features (`is_rainy`, `is_hot`, `is_cold`) were added, and performance improved.")
    lines.append("")

    lines.append("## 4. Model Input Features (from `feature_cols`)")
    lines.append("| feature | type | description |")
    lines.append("|---|---|---|")
    for c in feature_cols:
        t = "string" if c in categorical_cols else "number"
        desc = FEATURE_DESCRIPTIONS.get(c, "Model input feature")
        lines.append(f"| `{c}` | `{t}` | {desc} |")
    lines.append("")

    lines.append("## 5. Categorical Encoding")
    lines.append("- `plu_code`, `product_category` are LabelEncoded.")
    lines.append("- Use `label_maps` inside model bundle for consistent encoding.")
    lines.append("- Unknown category values should map to `-1`.")
    lines.append(f"- `plu_code` classes in label map: {len(label_maps.get('plu_code', {}))}")
    lines.append(f"- `product_category` classes in label map: {len(label_maps.get('product_category', {}))}")
    lines.append("")

    lines.append("## 6. Binary Weather Features")
    lines.append("- `is_rainy`: rain status flag (1 if rainy, else 0)")
    lines.append("- `is_hot`: hot day flag (1 if hot, else 0)")
    lines.append("- `is_cold`: cold day flag (1 if cold, else 0)")
    lines.append("")

    lines.append("## 7. Weather Inputs Needed from Spring Server")
    lines.append("- Provide `rainfall` directly, or provide `is_rainy` directly.")
    lines.append("- From `avg_temp`, server can derive `is_hot` and `is_cold`.")
    lines.append("- Derivation rules:")
    lines.append("  - `is_rainy = rainfall > 0`")
    lines.append("  - `is_hot = avg_temp >= 27`")
    lines.append("  - `is_cold = avg_temp <= 5`")
    lines.append("")

    lines.append("## 8. Sample Request JSON")
    lines.append("```json")
    lines.append(json.dumps(sample_request, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    lines.append("## 9. Sample Response JSON")
    lines.append("```json")
    lines.append(json.dumps(sample_response, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    lines.append("## 10. Order Recommendation Formula")
    lines.append("- `recommended_order_qty = ceil(predicted_sales_qty * 1.2)`")
    lines.append("")

    lines.append("## 11. Final Output File Paths")
    lines.append("- Prediction output: `outputs/reports/tomorrow_sales_prediction_final.csv`")
    lines.append("- Order recommendation output: `outputs/reports/order_recommendation_final.csv`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved final API spec: {OUT_MD}")
    print(f"Feature count: {len(feature_cols)}")


if __name__ == "__main__":
    main()
