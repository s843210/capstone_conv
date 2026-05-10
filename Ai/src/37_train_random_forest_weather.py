from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "model_features_weather.csv"

OUT_RESULT_JSON = BASE_DIR / "outputs" / "reports" / "random_forest_weather_result.json"
OUT_IMPORTANCE_CSV = BASE_DIR / "outputs" / "reports" / "random_forest_weather_feature_importance.csv"
OUT_SAMPLE_CSV = BASE_DIR / "outputs" / "reports" / "random_forest_weather_predictions_sample.csv"
OUT_MODEL = BASE_DIR / "outputs" / "models" / "random_forest_weather_model.pkl"

EXISTING_RF_FAST_METRICS = {
    "mae": 14.3009,
    "rmse": 26.2230,
    "r2": 0.5792,
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
    OUT_IMPORTANCE_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_MODEL.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    # 1) read + 2) time split prep
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    train_start = pd.Timestamp("2024-04-02")
    train_end = pd.Timestamp("2025-12-31")
    test_start = pd.Timestamp("2026-01-01")

    train_df = df[(df["date"] >= train_start) & (df["date"] <= train_end)].copy()
    test_df = df[df["date"] >= test_start].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Train or test split is empty.")

    # 3,4) target / exclude columns
    target_col = "target_sales"
    exclude_cols = {"date", "target_sales", "product_name", "product_name_norm"}
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    cat_cols = [c for c in ["plu_code", "product_category"] if c in feature_cols]
    num_cols = [c for c in feature_cols if c not in cat_cols]

    # Build X, y
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

    # 5) label encoding categorical
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

    # 6) train RF
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

    # 7) metrics
    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))

    # 9) compare with existing RF-fast
    compare = {
        "existing_rf_fast": EXISTING_RF_FAST_METRICS,
        "new_rf_weather": {"mae": mae, "rmse": rmse, "r2": r2},
        "delta": {
            "mae": mae - EXISTING_RF_FAST_METRICS["mae"],
            "rmse": rmse - EXISTING_RF_FAST_METRICS["rmse"],
            "r2": r2 - EXISTING_RF_FAST_METRICS["r2"],
        },
        "improved": {
            "mae": mae < EXISTING_RF_FAST_METRICS["mae"],
            "rmse": rmse < EXISTING_RF_FAST_METRICS["rmse"],
            "r2": r2 > EXISTING_RF_FAST_METRICS["r2"],
        },
    }

    # 10) save artifacts
    fi_df = pd.DataFrame(
        {"feature": feature_cols, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)
    fi_df.to_csv(OUT_IMPORTANCE_CSV, index=False, encoding="utf-8-sig")

    sample_cols = ["date", "plu_code", "product_name", "product_category", "target_sales"]
    sample_cols = [c for c in sample_cols if c in test_df.columns]
    sample_df = test_df.loc[X_test.index, sample_cols].copy()
    sample_df["prediction"] = preds
    sample_df = sample_df.sort_values(["date", "plu_code"]).head(500)
    sample_df["date"] = pd.to_datetime(sample_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    sample_df.to_csv(OUT_SAMPLE_CSV, index=False, encoding="utf-8-sig")

    # 11) save model bundle (do not overwrite existing fast model)
    bundle = {
        "model": model,
        "feature_cols": feature_cols,
        "categorical_cols": cat_cols,
        "label_maps": label_maps,
    }
    joblib.dump(bundle, OUT_MODEL)

    result = {
        "model": "RandomForestRegressor_weather",
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
        "comparison_with_existing_rf_fast": compare,
    }
    OUT_RESULT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 8) print train time and metrics
    print(f"Saved result json: {OUT_RESULT_JSON}")
    print(f"Saved feature importance: {OUT_IMPORTANCE_CSV}")
    print(f"Saved prediction sample: {OUT_SAMPLE_CSV}")
    print(f"Saved model: {OUT_MODEL}")
    print(f"Train seconds: {train_seconds:.2f}")
    print(f"RF-weather Test MAE: {mae:.6f}")
    print(f"RF-weather Test RMSE: {rmse:.6f}")
    print(f"RF-weather Test R2: {r2:.6f}")


if __name__ == "__main__":
    main()
