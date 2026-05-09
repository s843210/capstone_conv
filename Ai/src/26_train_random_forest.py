from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features.csv"
BASELINE_JSON = BASE_DIR / "outputs" / "reports" / "baseline_result.json"

OUT_RESULT_JSON = BASE_DIR / "outputs" / "reports" / "random_forest_result.json"
OUT_IMPORTANCE_CSV = BASE_DIR / "outputs" / "reports" / "random_forest_feature_importance.csv"
OUT_SAMPLE_CSV = BASE_DIR / "outputs" / "reports" / "random_forest_predictions_sample.csv"
OUT_MODEL = BASE_DIR / "outputs" / "models" / "random_forest_model.pkl"


def main() -> None:
    OUT_RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_IMPORTANCE_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_MODEL.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    # Split by requested time ranges
    train_start = pd.Timestamp("2024-04-02")
    train_end = pd.Timestamp("2025-12-31")
    test_start = pd.Timestamp("2026-01-01")

    train_df = df[(df["date"] >= train_start) & (df["date"] <= train_end)].copy()
    test_df = df[df["date"] >= test_start].copy()

    if train_df.empty or test_df.empty:
        raise ValueError("Train or test split is empty. Check date range in model_features.csv.")

    target_col = "target_sales"
    exclude_cols = {"date", "target_sales", "product_name", "product_name_norm"}
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    # Categorical columns explicitly requested
    categorical_cols = [c for c in ["plu_code", "product_category"] if c in feature_cols]
    numeric_cols = [c for c in feature_cols if c not in categorical_cols]

    X_train = train_df[feature_cols]
    y_train = pd.to_numeric(train_df[target_col], errors="coerce")
    X_test = test_df[feature_cols]
    y_test = pd.to_numeric(test_df[target_col], errors="coerce")

    valid_train_mask = y_train.notna()
    valid_test_mask = y_test.notna()
    X_train = X_train[valid_train_mask]
    y_train = y_train[valid_train_mask]
    X_test = X_test[valid_test_mask]
    y_test = y_test[valid_test_mask]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
            ("num", "passthrough", numeric_cols),
        ]
    )

    model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    fitted_n_jobs = -1
    try:
        pipeline.fit(X_train, y_train)
    except PermissionError:
        # Some restricted environments block multiprocessing resources.
        # Fallback to single-thread training while keeping same model settings otherwise.
        pipeline.set_params(model__n_jobs=1)
        pipeline.fit(X_train, y_train)
        fitted_n_jobs = 1
    preds = pipeline.predict(X_test)

    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))

    # Baseline metrics from prior report (fallback: compute from rolling_mean_7 on same test split)
    baseline_metrics = {"mae": None, "rmse": None, "r2": None}
    if BASELINE_JSON.exists():
        try:
            baseline_obj = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
            base = baseline_obj.get("metrics_test", {})
            baseline_metrics = {
                "mae": base.get("mae"),
                "rmse": base.get("rmse"),
                "r2": base.get("r2"),
            }
        except Exception:
            pass
    if baseline_metrics["mae"] is None:
        base_pred = pd.to_numeric(test_df["rolling_mean_7"], errors="coerce")
        m = y_test.notna() & base_pred.notna()
        baseline_metrics = {
            "mae": float(mean_absolute_error(y_test[m], base_pred[m])),
            "rmse": float(np.sqrt(mean_squared_error(y_test[m], base_pred[m]))),
            "r2": float(r2_score(y_test[m], base_pred[m])),
        }

    # Feature importance
    ohe = pipeline.named_steps["preprocessor"].named_transformers_["cat"]
    cat_feature_names = []
    if categorical_cols:
        cat_feature_names = ohe.get_feature_names_out(categorical_cols).tolist()
    all_feature_names = cat_feature_names + numeric_cols
    importances = pipeline.named_steps["model"].feature_importances_
    fi_df = pd.DataFrame(
        {
            "feature": all_feature_names,
            "importance": importances,
        }
    ).sort_values("importance", ascending=False)
    fi_df.to_csv(OUT_IMPORTANCE_CSV, index=False, encoding="utf-8-sig")

    # Prediction sample
    sample_cols = ["date", "plu_code", "product_name", "product_category", "target_sales"]
    sample_cols = [c for c in sample_cols if c in test_df.columns]
    sample_df = test_df.loc[X_test.index, sample_cols].copy()
    sample_df["prediction"] = preds
    sample_df = sample_df.sort_values(["date", "plu_code"]).head(500)
    sample_df.to_csv(OUT_SAMPLE_CSV, index=False, encoding="utf-8-sig")

    # Save model pipeline
    joblib.dump(pipeline, OUT_MODEL)

    result = {
        "model": "RandomForestRegressor",
        "params": {
            "n_estimators": 300,
            "random_state": 42,
            "n_jobs": -1,
        },
        "runtime": {
            "fitted_n_jobs": fitted_n_jobs,
        },
        "split": {
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_start": str(test_start.date()),
        },
        "rows": {
            "train": int(len(X_train)),
            "test": int(len(X_test)),
        },
        "metrics_test": {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
        },
        "baseline_metrics_test": baseline_metrics,
    }
    OUT_RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved result json: {OUT_RESULT_JSON}")
    print(f"Saved feature importance: {OUT_IMPORTANCE_CSV}")
    print(f"Saved prediction sample: {OUT_SAMPLE_CSV}")
    print(f"Saved model: {OUT_MODEL}")
    print(f"RF Test MAE: {mae:.6f}")
    print(f"RF Test RMSE: {rmse:.6f}")
    print(f"RF Test R2: {r2:.6f}")


if __name__ == "__main__":
    main()
