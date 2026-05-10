from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_semester_binary_model.pkl"
MODEL_FEATURES_CSV = BASE_DIR / "data" / "processed" / "model_features_semester_binary.csv"
PREDICTION_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction_final.csv"
ORDER_CSV = BASE_DIR / "outputs" / "reports" / "order_recommendation_final.csv"

OUT_API_MD = BASE_DIR / "outputs" / "reports" / "model_api_spec_semester_final.md"
OUT_SUMMARY_TXT = BASE_DIR / "outputs" / "reports" / "final_model_summary_semester.txt"

FINAL_METRICS = {
    "mae": 13.0240,
    "rmse": 24.7452,
    "r2": 0.6253,
}
OLD_FINAL_METRICS = {
    "mae": 12.8477,
    "rmse": 24.1966,
    "r2": 0.6417,
}

FEATURE_DESC = {
    "plu_code": "Product PLU code (string -> label encoded)",
    "product_category": "Product category (string -> label encoded)",
    "sales_qty": "Current observed sales quantity",
    "purchase_qty": "Current observed purchase quantity",
    "class_count": "Class count for current weekday",
    "monday_class_count": "Monday class count",
    "tuesday_class_count": "Tuesday class count",
    "wednesday_class_count": "Wednesday class count",
    "thursday_class_count": "Thursday class count",
    "friday_class_count": "Friday class count",
    "is_semester": "1 when not vacation, 0 when vacation",
    "is_rainy": "1 if rainfall > 0 else 0",
    "is_hot": "1 if avg_temp >= 27 else 0",
    "is_cold": "1 if avg_temp <= 5 else 0",
    "year": "Year extracted from date",
    "month": "Month extracted from date",
    "day": "Day extracted from date",
    "weekday": "Weekday index (Mon=0 ... Sun=6)",
    "is_weekend": "Weekend flag",
    "sales_lag_1": "Lag-1 sales of same plu_code",
    "sales_lag_7": "Lag-7 sales of same plu_code",
    "rolling_mean_7": "Rolling mean over previous 7 points after shift(1)",
    "rolling_mean_14": "Rolling mean over previous 14 points after shift(1)",
    "rolling_mean_28": "Rolling mean over previous 28 points after shift(1)",
}


def main() -> None:
    OUT_API_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY_TXT.parent.mkdir(parents=True, exist_ok=True)

    for p in [MODEL_PATH, MODEL_FEATURES_CSV, PREDICTION_CSV, ORDER_CSV]:
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    bundle = joblib.load(MODEL_PATH)
    feature_cols = bundle.get("feature_cols", [])
    categorical_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})
    if not feature_cols:
        raise ValueError("feature_cols not found in model bundle")

    df = pd.read_csv(MODEL_FEATURES_CSV, low_memory=False)
    if df.empty:
        raise ValueError("model_features_semester_binary.csv is empty")
    sample_row = df.iloc[0]

    sample_features: dict[str, object] = {}
    for c in feature_cols:
        v = sample_row.get(c, 0)
        if c in categorical_cols:
            sample_features[c] = str(v)
        else:
            sample_features[c] = float(v) if pd.notna(v) else 0.0

    base_date = str(sample_row.get("date", "2026-02-01"))
    predict_date = (pd.to_datetime(base_date, errors="coerce") + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    sample_request = {
        "base_date": base_date,
        "weather_input": {
            "rainfall": 0.5,
            "avg_temp": 22.0,
            "derived_binary": {
                "is_rainy": 1,
                "is_hot": 0,
                "is_cold": 0,
            },
        },
        "academic_input": {
            "is_vacation": 0,
            "derived_is_semester": 1,
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
        "base_date": base_date,
        "predict_date": predict_date,
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

    # API spec markdown
    md: list[str] = []
    md.append("# Final Model API Spec (Semester Binary)")
    md.append("")
    md.append("## 1. Final Model")
    md.append("- Model path: `outputs/models/random_forest_semester_binary_model.pkl`")
    md.append("- Model type: `RandomForestRegressor`")
    md.append("- Bundle keys: `model`, `feature_cols`, `categorical_cols`, `label_maps`")
    md.append("")

    md.append("## 2. Final Performance")
    md.append(f"- MAE: {FINAL_METRICS['mae']}")
    md.append(f"- RMSE: {FINAL_METRICS['rmse']}")
    md.append(f"- R2: {FINAL_METRICS['r2']}")
    md.append("")

    md.append("## 3. Input Features")
    md.append("### feature_cols")
    md.append("| feature | type | description |")
    md.append("|---|---|---|")
    for c in feature_cols:
        dtype = "string" if c in categorical_cols else "number"
        md.append(f"| `{c}` | `{dtype}` | {FEATURE_DESC.get(c, 'Model feature')} |")
    md.append("")

    md.append("### categorical_cols")
    for c in categorical_cols:
        md.append(f"- `{c}`")
    md.append("")

    md.append("## 4. Label Encoding (label_maps)")
    md.append("- `plu_code` and `product_category` must be encoded using `label_maps` from model bundle.")
    md.append("- Unknown values should be mapped to `-1`.")
    md.append(f"- `plu_code` class count: {len(label_maps.get('plu_code', {}))}")
    md.append(f"- `product_category` class count: {len(label_maps.get('product_category', {}))}")
    md.append("")

    md.append("## 5. Rule Features")
    md.append("### is_semester")
    md.append("- Rule: `is_vacation == 1` -> `is_semester = 0`, otherwise `is_semester = 1`")
    md.append("### binary weather")
    md.append("- `is_rainy = rainfall > 0`")
    md.append("- `is_hot = avg_temp >= 27`")
    md.append("- `is_cold = avg_temp <= 5`")
    md.append("")

    md.append("## 6. Order Recommendation Formula")
    md.append("- `recommended_order_qty = ceil(predicted_sales_qty * 1.2)`")
    md.append("- if `predicted_sales_qty <= 0`, then `recommended_order_qty = 0`")
    md.append("")

    md.append("## 7. Sample Request JSON")
    md.append("```json")
    md.append(json.dumps(sample_request, ensure_ascii=False, indent=2))
    md.append("```")
    md.append("")

    md.append("## 8. Sample Response JSON")
    md.append("```json")
    md.append(json.dumps(sample_response, ensure_ascii=False, indent=2))
    md.append("```")
    md.append("")

    md.append("## 9. FastAPI Handoff Notes")
    md.append("1. Load model bundle once at app startup.")
    md.append("2. Build runtime features in exact `feature_cols` order.")
    md.append("3. Apply `label_maps` to categorical columns; unknown -> `-1`.")
    md.append("4. Cast numeric columns to float/int and fill missing with `0`.")
    md.append("5. Run `model.predict`, clip negatives to `0`, then compute order recommendation.")
    md.append("6. Persist prediction and recommendation outputs to report files if needed.")

    OUT_API_MD.write_text("\n".join(md), encoding="utf-8")

    # Summary text
    summary: list[str] = []
    summary.append("Final Model Summary (Semester Binary)")
    summary.append(f"final_model_name: {MODEL_PATH.name}")
    summary.append(f"final_model_path: {MODEL_PATH.as_posix()}")
    summary.append("")
    summary.append("[Final Performance]")
    summary.append(f"MAE: {FINAL_METRICS['mae']}")
    summary.append(f"RMSE: {FINAL_METRICS['rmse']}")
    summary.append(f"R2: {FINAL_METRICS['r2']}")
    summary.append("")
    summary.append("[Used Features]")
    for c in feature_cols:
        summary.append(f"- {c}")
    summary.append("")
    summary.append("[is_semester Rule]")
    summary.append("- if is_vacation == 1: is_semester = 0")
    summary.append("- else: is_semester = 1")
    summary.append("")
    summary.append("[Binary Weather Rules]")
    summary.append("- is_rainy = rainfall > 0")
    summary.append("- is_hot = avg_temp >= 27")
    summary.append("- is_cold = avg_temp <= 5")
    summary.append("")
    summary.append("[Difference vs Previous Final Model (RF + Binary Weather)]")
    summary.append("- Academic features simplified to single `is_semester`")
    summary.append("- Removed dead academic features: is_exam, is_festival, is_start_semester, is_end_semester, is_holiday_or_no_class, is_vacation")
    summary.append(
        f"- Metric change: MAE {OLD_FINAL_METRICS['mae']} -> {FINAL_METRICS['mae']}, "
        f"RMSE {OLD_FINAL_METRICS['rmse']} -> {FINAL_METRICS['rmse']}, "
        f"R2 {OLD_FINAL_METRICS['r2']} -> {FINAL_METRICS['r2']}"
    )
    summary.append("")
    summary.append("[Final Selection Reasons]")
    summary.append("- Performance gap vs previous final model is small")
    summary.append("- Better maintainability and explainability from simplified academic feature design")
    summary.append("- Dead feature removal")
    summary.append("- Easier feature management in production operations")

    OUT_SUMMARY_TXT.write_text("\n".join(summary), encoding="utf-8")

    print(f"Saved semester API spec: {OUT_API_MD}")
    print(f"Saved semester final summary: {OUT_SUMMARY_TXT}")
    print(f"Feature count: {len(feature_cols)}")


if __name__ == "__main__":
    main()
