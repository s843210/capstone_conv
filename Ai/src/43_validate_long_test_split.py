from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_weather_binary.csv"
OUT_RESULT_JSON = BASE_DIR / "outputs" / "reports" / "random_forest_weather_binary_long_test_result.json"

FINAL_MODEL_METRICS = {
    "mae": 12.8477,
    "rmse": 24.1966,
    "r2": 0.6417,
}


def label_encode_train_test(
    train_s: pd.Series, test_s: pd.Series
) -> tuple[pd.Series, pd.Series, dict[str, int]]:
    train_vals = train_s.astype(str).fillna("")
    test_vals = test_s.astype(str).fillna("")
    classes = sorted(train_vals.unique().tolist())
    mapping = {v: i for i, v in enumerate(classes)}
    train_enc = train_vals.map(mapping).fillna(-1).astype(int)
    test_enc = test_vals.map(mapping).fillna(-1).astype(int)
    return train_enc, test_enc, mapping


def main() -> None:
    OUT_RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    train_start = pd.Timestamp("2024-04-02")
    train_end = pd.Timestamp("2025-08-31")
    test_start = pd.Timestamp("2025-09-01")
    test_end = pd.Timestamp("2026-03-31")

    train_df = df[(df["date"] >= train_start) & (df["date"] <= train_end)].copy()
    test_df = df[(df["date"] >= test_start) & (df["date"] <= test_end)].copy()

    if train_df.empty or test_df.empty:
        raise ValueError("Train or test split is empty for long-test validation split.")

    target_col = "target_sales"
    exclude_cols = {"date", "target_sales", "product_name", "product_name_norm"}
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    cat_cols = [c for c in ["plu_code", "product_category"] if c in feature_cols]
    num_cols = [c for c in feature_cols if c not in cat_cols]

    X_train = train_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()
    y_train = pd.to_numeric(train_df[target_col], errors="coerce")
    y_test = pd.to_numeric(test_df[target_col], errors="coerce")

    valid_train = y_train.notna()
    valid_test = y_test.notna()
    X_train = X_train[valid_train].copy()
    y_train = y_train[valid_train].copy()
    X_test = X_test[valid_test].copy()
    y_test = y_test[valid_test].copy()

    label_maps: dict[str, dict[str, int]] = {}
    for c in cat_cols:
        tr_enc, te_enc, mapping = label_encode_train_test(X_train[c], X_test[c])
        X_train[c] = tr_enc
        X_test[c] = te_enc
        label_maps[c] = mapping

    for c in num_cols:
        X_train[c] = pd.to_numeric(X_train[c], errors="coerce")
        X_test[c] = pd.to_numeric(X_test[c], errors="coerce")

    X_train = X_train.fillna(0)
    X_test = X_test.fillna(0)

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=20,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )

    start = time.perf_counter()
    fitted_n_jobs = -1
    try:
        model.fit(X_train, y_train)
    except PermissionError:
        model.set_params(n_jobs=1)
        model.fit(X_train, y_train)
        fitted_n_jobs = 1
    train_seconds = time.perf_counter() - start

    preds = model.predict(X_test)

    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))

    compare = {
        "final_model_reference": FINAL_MODEL_METRICS,
        "long_test_validation": {"mae": mae, "rmse": rmse, "r2": r2},
        "delta": {
            "mae": mae - FINAL_MODEL_METRICS["mae"],
            "rmse": rmse - FINAL_MODEL_METRICS["rmse"],
            "r2": r2 - FINAL_MODEL_METRICS["r2"],
        },
        "improved": {
            "mae": mae < FINAL_MODEL_METRICS["mae"],
            "rmse": rmse < FINAL_MODEL_METRICS["rmse"],
            "r2": r2 > FINAL_MODEL_METRICS["r2"],
        },
    }

    result = {
        "experiment": "random_forest_weather_binary_long_test_validation",
        "input_csv": INPUT_CSV.as_posix(),
        "params": {
            "n_estimators": 100,
            "max_depth": 20,
            "min_samples_leaf": 3,
            "random_state": 42,
            "n_jobs": -1,
        },
        "runtime": {
            "train_seconds": train_seconds,
            "fitted_n_jobs": fitted_n_jobs,
        },
        "split": {
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_start": str(test_start.date()),
            "test_end": str(test_end.date()),
        },
        "rows": {
            "train": int(len(X_train)),
            "test": int(len(X_test)),
        },
        "features": {
            "count": len(feature_cols),
            "categorical_cols": cat_cols,
            "feature_cols": feature_cols,
        },
        "metrics_test": {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
        },
        "comparison_with_final_model": compare,
    }

    OUT_RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved long-test result json: {OUT_RESULT_JSON}")
    print(f"Train rows: {len(X_train)}")
    print(f"Test rows: {len(X_test)}")
    print(f"Train seconds: {train_seconds:.2f}")
    print(f"Long-test MAE: {mae:.6f}")
    print(f"Long-test RMSE: {rmse:.6f}")
    print(f"Long-test R2: {r2:.6f}")


if __name__ == "__main__":
    main()
