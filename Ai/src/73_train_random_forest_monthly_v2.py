from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_monthly_v2.csv"
RESULT_JSON = BASE_DIR / "outputs" / "reports" / "random_forest_monthly_v2_result.json"
FEATURE_IMPORTANCE_CSV = BASE_DIR / "outputs" / "reports" / "random_forest_monthly_v2_feature_importance.csv"
PRED_SAMPLE_CSV = BASE_DIR / "outputs" / "reports" / "random_forest_monthly_v2_predictions_sample.csv"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_monthly_v2_model.pkl"

TRAIN_START = pd.Timestamp("2024-03-29")
TRAIN_END = pd.Timestamp("2025-09-30")
TEST_START = pd.Timestamp("2025-10-01")
TEST_END = pd.Timestamp("2026-04-29")

TARGET_COL = "target_sales"
DROP_COLS = ["date", TARGET_COL, "product_name", "product_name_norm"]
CATEGORICAL_COLS = ["plu_code", "product_category"]


def main() -> None:
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    FEATURE_IMPORTANCE_CSV.parent.mkdir(parents=True, exist_ok=True)
    PRED_SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    if "date" not in df.columns:
        raise KeyError("'date' column not found.")
    if TARGET_COL not in df.columns:
        raise KeyError(f"'{TARGET_COL}' column not found.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce")
    df = df[df["date"].notna() & df[TARGET_COL].notna()].copy()

    train_mask = (df["date"] >= TRAIN_START) & (df["date"] <= TRAIN_END)
    test_mask = (df["date"] >= TEST_START) & (df["date"] <= TEST_END)
    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()

    if train_df.empty:
        raise ValueError("Train split is empty.")
    if test_df.empty:
        raise ValueError("Test split is empty.")

    drop_cols_existing = [c for c in DROP_COLS if c in df.columns]
    feature_cols = [c for c in df.columns if c not in drop_cols_existing]

    X_train = train_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()
    y_train = train_df[TARGET_COL].copy()
    y_test = test_df[TARGET_COL].copy()

    # LabelEncoding for categorical columns using train-fit, unknown -> -1.
    encoders: dict[str, LabelEncoder] = {}
    for col in CATEGORICAL_COLS:
        if col not in X_train.columns:
            continue
        le = LabelEncoder()
        train_vals = X_train[col].astype(str).fillna("")
        le.fit(train_vals)
        encoders[col] = le

        mapping = {cls: idx for idx, cls in enumerate(le.classes_)}
        X_train[col] = train_vals.map(mapping).astype(int)
        X_test[col] = X_test[col].astype(str).fillna("").map(mapping).fillna(-1).astype(int)

    # Numeric coercion for the rest.
    for col in X_train.columns:
        if col in CATEGORICAL_COLS:
            continue
        X_train[col] = pd.to_numeric(X_train[col], errors="coerce")
        X_test[col] = pd.to_numeric(X_test[col], errors="coerce")

    # Remove any residual NaN rows to ensure sklearn fit stability.
    train_valid = X_train.notna().all(axis=1) & y_train.notna()
    test_valid = X_test.notna().all(axis=1) & y_test.notna()
    X_train = X_train[train_valid]
    y_train = y_train[train_valid]
    X_test = X_test[test_valid]
    y_test = y_test[test_valid]
    test_dates = test_df.loc[test_valid, "date"]
    test_plu = test_df.loc[test_valid, "plu_code"].astype(str)

    start_time = time.time()
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=20,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    elapsed = time.time() - start_time

    mae = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred) ** 0.5
    r2 = r2_score(y_test, y_pred)

    fi = pd.DataFrame(
        {"feature": X_train.columns, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)
    fi.to_csv(FEATURE_IMPORTANCE_CSV, index=False, encoding="utf-8-sig")

    pred_sample = pd.DataFrame(
        {
            "date": test_dates.dt.strftime("%Y-%m-%d").values,
            "plu_code": test_plu.values,
            "y_true": y_test.values,
            "y_pred": y_pred,
        }
    ).head(500)
    pred_sample.to_csv(PRED_SAMPLE_CSV, index=False, encoding="utf-8-sig")

    model_bundle = {
        "model": model,
        "feature_columns": X_train.columns.tolist(),
        "categorical_columns": [c for c in CATEGORICAL_COLS if c in X_train.columns],
        "label_encoders": encoders,
        "train_period": [str(TRAIN_START.date()), str(TRAIN_END.date())],
        "test_period": [str(TEST_START.date()), str(TEST_END.date())],
    }
    joblib.dump(model_bundle, MODEL_PATH)

    result = {
        "input_csv": INPUT_CSV.as_posix(),
        "train_period": [str(TRAIN_START.date()), str(TRAIN_END.date())],
        "test_period": [str(TEST_START.date()), str(TEST_END.date())],
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "feature_count": int(X_train.shape[1]),
        "metrics": {
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2),
        },
        "train_time_seconds": float(elapsed),
        "outputs": {
            "result_json": RESULT_JSON.as_posix(),
            "feature_importance_csv": FEATURE_IMPORTANCE_CSV.as_posix(),
            "predictions_sample_csv": PRED_SAMPLE_CSV.as_posix(),
            "model_path": MODEL_PATH.as_posix(),
        },
    }
    RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved result json: {RESULT_JSON}")
    print(f"Saved feature importance: {FEATURE_IMPORTANCE_CSV}")
    print(f"Saved prediction sample: {PRED_SAMPLE_CSV}")
    print(f"Saved model: {MODEL_PATH}")
    print(f"Train rows: {len(X_train)}, Test rows: {len(X_test)}")
    print(f"MAE: {mae:.6f}, RMSE: {rmse:.6f}, R2: {r2:.6f}")
    print(f"Train time (sec): {elapsed:.4f}")


if __name__ == "__main__":
    main()
