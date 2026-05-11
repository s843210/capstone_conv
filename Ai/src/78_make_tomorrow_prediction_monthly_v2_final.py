from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_monthly_v2.csv"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_monthly_v2_model.pkl"
OUTPUT_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction_monthly_v2_final.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction_monthly_v2_final_report.txt"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input not found: {INPUT_CSV}")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    if "date" not in df.columns:
        raise KeyError("'date' column not found in input.")
    if "plu_code" not in df.columns:
        raise KeyError("'plu_code' column not found in input.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()
    df = df.sort_values(["plu_code", "date"])

    # 1) 각 plu_code별 최신 행 선택
    latest_idx = df.groupby("plu_code")["date"].idxmax()
    latest = df.loc[latest_idx].copy().sort_values("plu_code").reset_index(drop=True)

    # 2) predict_date 생성
    latest["predict_date"] = latest["date"] + pd.Timedelta(days=1)

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]

    # 3) 모델 번들 내부 키를 유연하게 읽기
    feature_cols = bundle.get("feature_cols", bundle.get("feature_columns"))
    categorical_cols = bundle.get("categorical_cols", bundle.get("categorical_columns", []))
    label_maps = bundle.get("label_maps")
    label_encoders = bundle.get("label_encoders")

    if feature_cols is None:
        raise KeyError("Model bundle does not contain feature_cols/feature_columns.")

    X = latest.copy()
    missing_feature_cols = [c for c in feature_cols if c not in X.columns]
    if missing_feature_cols:
        raise KeyError(f"Missing feature columns in input latest rows: {missing_feature_cols}")
    X = X[feature_cols].copy()

    # categorical encoding
    for col in categorical_cols:
        if col not in X.columns:
            continue
        if label_maps is not None and col in label_maps:
            mp: Dict[str, int] = label_maps[col]
            X[col] = X[col].astype(str).map(mp).fillna(-1).astype(int)
        elif label_encoders is not None and col in label_encoders:
            le = label_encoders[col]
            mp = {cls: i for i, cls in enumerate(le.classes_)}
            X[col] = X[col].astype(str).map(mp).fillna(-1).astype(int)
        else:
            # fallback: unknown mapping path
            X[col] = X[col].astype("category").cat.codes

    for col in X.columns:
        if col in categorical_cols:
            continue
        X[col] = pd.to_numeric(X[col], errors="coerce")

    valid_mask = X.notna().all(axis=1)
    valid_X = X[valid_mask]
    valid_latest = latest.loc[valid_mask].copy()

    preds = model.predict(valid_X)
    pred_series = pd.Series(preds, index=valid_latest.index, name="predicted_sales_qty")
    pred_series = pred_series.clip(lower=0)  # 5) 음수 보정

    out = valid_latest.copy()
    out["predicted_sales_qty"] = pred_series.values
    out_df = pd.DataFrame(
        {
            "base_date": out["date"].dt.strftime("%Y-%m-%d"),
            "predict_date": out["predict_date"].dt.strftime("%Y-%m-%d"),
            "plu_code": out["plu_code"].astype(str),
            "product_name": out.get("product_name", ""),
            "product_category": out.get("product_category", ""),
            "predicted_sales_qty": out["predicted_sales_qty"].astype(float),
        }
    )
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    report_lines: List[str] = []
    report_lines.append("Tomorrow Sales Prediction Monthly V2 Final Report")
    report_lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    report_lines.append(f"model_path: {MODEL_PATH.as_posix()}")
    report_lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    report_lines.append(f"latest_sku_rows_total: {len(latest)}")
    report_lines.append(f"latest_rows_used_for_prediction: {len(out_df)}")
    report_lines.append(f"excluded_rows_due_to_missing_features: {len(latest) - len(out_df)}")
    if len(out_df) > 0:
        report_lines.append(f"base_date_min: {out_df['base_date'].min()}")
        report_lines.append(f"base_date_max: {out_df['base_date'].max()}")
        report_lines.append(f"predict_date_min: {out_df['predict_date'].min()}")
        report_lines.append(f"predict_date_max: {out_df['predict_date'].max()}")
        report_lines.append(f"pred_min: {out_df['predicted_sales_qty'].min()}")
        report_lines.append(f"pred_max: {out_df['predicted_sales_qty'].max()}")
        report_lines.append(f"pred_mean: {out_df['predicted_sales_qty'].mean()}")
        report_lines.append(f"pred_median: {out_df['predicted_sales_qty'].median()}")
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Saved prediction csv: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Predicted rows: {len(out_df)}")


if __name__ == "__main__":
    main()
