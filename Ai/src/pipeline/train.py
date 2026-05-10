"""Train — baseline, RandomForest, LightGBM training and model comparison.

Consolidates logic from legacy scripts 25, 26_fast, 27, 28.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ..config import Paths, Training
from ..utils.io import safe_read_csv, safe_save_csv, ensure_dir
from ..utils.encoding import label_encode_train_test
from ..utils.report import write_report


# ===================================================================
# Helpers
# ===================================================================

def _split_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Time-based train/test split."""
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()

    train_start = pd.Timestamp(Training.TRAIN_START)
    train_end = pd.Timestamp(Training.TRAIN_END)
    test_start = pd.Timestamp(Training.TEST_START)

    train = df[(df["date"] >= train_start) & (df["date"] <= train_end)].copy()
    test = df[df["date"] >= test_start].copy()

    if train.empty or test.empty:
        raise ValueError("Train or test split is empty.")
    return train, test


def _prepare_xy(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    all_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, list[str], list[str], dict]:
    """Build X/y matrices with label-encoding for categorical columns."""
    target = Training.TARGET_COL
    exclude = {"date", target, "product_name", "product_name_norm"}
    feature_cols = [c for c in all_columns if c not in exclude]

    cat_cols = [c for c in ["plu_code", "product_category"] if c in feature_cols]
    num_cols = [c for c in feature_cols if c not in cat_cols]

    X_train = train_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()
    y_train = pd.to_numeric(train_df[target], errors="coerce")
    y_test = pd.to_numeric(test_df[target], errors="coerce")

    valid_tr = y_train.notna()
    valid_te = y_test.notna()
    X_train, y_train = X_train[valid_tr].copy(), y_train[valid_tr].copy()
    X_test, y_test = X_test[valid_te].copy(), y_test[valid_te].copy()

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

    return X_train, X_test, y_train, y_test, feature_cols, cat_cols, label_maps


def _metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


# ===================================================================
# Baseline  (legacy 25)
# ===================================================================

def train_baseline(input_csv: Path | None = None) -> dict:
    """Evaluate the rolling_mean_7 baseline."""
    input_csv = input_csv or Paths.MODEL_FEATURES_WEATHER_BINARY
    out_json = Paths.REPORTS_DIR / "baseline_result.json"

    df = safe_read_csv(input_csv)
    train_df, test_df = _split_data(df)

    test_df = test_df.copy()
    test_df["target_sales"] = pd.to_numeric(test_df["target_sales"], errors="coerce")
    test_df["baseline_pred"] = pd.to_numeric(test_df["rolling_mean_7"], errors="coerce")
    valid = test_df["target_sales"].notna() & test_df["baseline_pred"].notna()
    test_df = test_df[valid]

    m = _metrics(test_df["target_sales"], test_df["baseline_pred"].values)

    result = {
        "model": "baseline_rolling_mean_7",
        "rows": {"train": len(train_df), "test": len(test_df)},
        "metrics_test": m,
    }
    ensure_dir(out_json)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Baseline - MAE: {m['mae']:.4f}, RMSE: {m['rmse']:.4f}, R2: {m['r2']:.4f}")
    return result


# ===================================================================
# RandomForest  (legacy 26_fast)
# ===================================================================

def train_random_forest_weather_binary(input_csv: Path | None = None) -> dict:
    """Train a RandomForestRegressor with weather binary features and save the model bundle."""
    input_csv = input_csv or Paths.MODEL_FEATURES_WEATHER_BINARY
    out_model = Paths.MODEL_RF_FAST  # config에서 rf_fast가 weather_binary로 연결됨
    out_json = Paths.REPORTS_DIR / "random_forest_weather_binary_result.json"
    out_fi = Paths.REPORTS_DIR / "random_forest_weather_binary_feature_importance.csv"

    df = safe_read_csv(input_csv)
    train_df, test_df = _split_data(df)
    X_train, X_test, y_train, y_test, feat_cols, cat_cols, label_maps = _prepare_xy(
        train_df, test_df, df.columns.tolist()
    )

    params = Training.RF_PARAMS
    model = RandomForestRegressor(
        n_estimators=params.get("n_estimators", 100),
        max_depth=params.get("max_depth", 20),
        min_samples_leaf=params.get("min_samples_leaf", 3),
        random_state=params.get("random_state", 42),
        n_jobs=-1,
    )

    start = time.perf_counter()
    try:
        model.fit(X_train, y_train)
    except PermissionError:
        model.set_params(n_jobs=1)
        model.fit(X_train, y_train)
    elapsed = time.perf_counter() - start

    preds = model.predict(X_test)
    m = _metrics(y_test, preds)

    # Feature importance
    fi = pd.DataFrame({"feature": feat_cols, "importance": model.feature_importances_})
    fi = fi.sort_values("importance", ascending=False)
    safe_save_csv(fi, out_fi)

    # Save bundle
    bundle = {"model": model, "feature_cols": feat_cols, "categorical_cols": cat_cols, "label_maps": label_maps}
    ensure_dir(out_model)
    joblib.dump(bundle, out_model)

    result = {
        "model": "RandomForestRegressor_weather_binary",
        "params": params,
        "runtime": {"train_seconds": elapsed},
        "rows": {"train": len(X_train), "test": len(X_test)},
        "metrics_test": m,
    }
    ensure_dir(out_json)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"RF-Weather-Binary - MAE: {m['mae']:.4f}, RMSE: {m['rmse']:.4f}, R2: {m['r2']:.4f} ({elapsed:.1f}s)")
    return result


# ===================================================================
# LightGBM  (legacy 27)
# ===================================================================

def train_lightgbm(input_csv: Path | None = None) -> dict:
    """Train a LightGBM regressor and save the model bundle."""
    try:
        from lightgbm import LGBMRegressor
    except ImportError as exc:
        raise ImportError("lightgbm is required: pip install lightgbm") from exc

    input_csv = input_csv or Paths.MODEL_FEATURES_WEATHER_BINARY
    out_model = Paths.MODEL_LIGHTGBM
    out_json = Paths.REPORTS_DIR / "lightgbm_result.json"
    out_fi = Paths.REPORTS_DIR / "lightgbm_feature_importance.csv"

    df = safe_read_csv(input_csv)
    train_df, test_df = _split_data(df)
    X_train, X_test, y_train, y_test, feat_cols, cat_cols, label_maps = _prepare_xy(
        train_df, test_df, df.columns.tolist()
    )

    params = Training.LGBM_PARAMS
    model = LGBMRegressor(
        n_estimators=params.get("n_estimators", 500),
        learning_rate=params.get("learning_rate", 0.05),
        max_depth=params.get("max_depth", -1),
        random_state=params.get("random_state", 42),
    )

    start = time.perf_counter()
    model.fit(X_train, y_train)
    elapsed = time.perf_counter() - start

    preds = model.predict(X_test)
    m = _metrics(y_test, preds)

    fi = pd.DataFrame({"feature": feat_cols, "importance": model.feature_importances_})
    fi = fi.sort_values("importance", ascending=False)
    safe_save_csv(fi, out_fi)

    bundle = {"model": model, "feature_cols": feat_cols, "categorical_cols": cat_cols, "label_maps": label_maps}
    ensure_dir(out_model)
    joblib.dump(bundle, out_model)

    result = {
        "model": "LightGBMRegressor",
        "params": params,
        "runtime": {"train_seconds": elapsed},
        "rows": {"train": len(X_train), "test": len(X_test)},
        "metrics_test": m,
    }
    ensure_dir(out_json)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"LightGBM - MAE: {m['mae']:.4f}, RMSE: {m['rmse']:.4f}, R2: {m['r2']:.4f} ({elapsed:.1f}s)")
    return result


# ===================================================================
# Compare models  (legacy 28)
# ===================================================================

def compare_models() -> pd.DataFrame:
    """Load all model result JSONs and produce a comparison table."""
    out_csv = Paths.REPORTS_DIR / "model_comparison.csv"
    json_files = sorted(Paths.REPORTS_DIR.glob("*_result.json"))

    rows = []
    for jf in json_files:
        try:
            obj = json.loads(jf.read_text(encoding="utf-8"))
            m = obj.get("metrics_test", {})
            rows.append({
                "model": obj.get("model", jf.stem),
                "mae": m.get("mae"),
                "rmse": m.get("rmse"),
                "r2": m.get("r2"),
            })
        except Exception:
            pass

    if not rows:
        print("No model result JSONs found.")
        return pd.DataFrame()

    comp = pd.DataFrame(rows).sort_values("mae")
    safe_save_csv(comp, out_csv)
    print("\n=== Model Comparison ===")
    print(comp.to_string(index=False))
    return comp
