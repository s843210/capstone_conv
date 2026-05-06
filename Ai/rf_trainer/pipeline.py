from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .metrics import compute_metrics


FEATURE_COLUMNS = [
    "lag_1",
    "lag_3",
    "lag_7",
    "rolling_7_mean",
    "rolling_7_std",
    "day_of_week",
    "tomorrow_day_of_week",
    "month",
    "is_holiday",
    "tomorrow_is_weekend",
    "tomorrow_is_holiday",
    "academic_event",
    "tomorrow_academic_event",
    "weekday_to_weekend",
    "weekend_to_weekday",
    "building_headcount",
    "category_l",
    "category_m",
]
NUMERIC_COLUMNS = [c for c in FEATURE_COLUMNS if c not in ("category_l", "category_m")]
CATEGORICAL_COLUMNS = ["category_l", "category_m"]


@dataclass
class SplitData:
    train: pd.DataFrame
    valid: pd.DataFrame


def build_features_from_sales(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    base["date"] = pd.to_datetime(base["date"])
    if "plu_code" not in base.columns:
        raise ValueError("plu_code column is required. Provide product_name->plu_code mapping first.")
    if "category_l" not in base.columns:
        base["category_l"] = base["category_m"]

    base = base.sort_values(["plu_code", "date"]).reset_index(drop=True)
    g = base.groupby("plu_code", dropna=False)["sales"]
    base["lag_1"] = g.shift(1)
    base["lag_3"] = g.shift(3)
    base["lag_7"] = g.shift(7)
    base["rolling_7_mean"] = g.shift(1).rolling(7, min_periods=1).mean()
    base["rolling_7_std"] = g.shift(1).rolling(7, min_periods=1).std().fillna(0.0)
    base["day_of_week"] = base["date"].dt.dayofweek
    base["tomorrow_day_of_week"] = (base["day_of_week"] + 1) % 7
    base["month"] = base["date"].dt.month
    base["is_holiday"] = (base["day_of_week"] >= 5).astype(int)
    base["tomorrow_is_weekend"] = (base["tomorrow_day_of_week"] >= 5).astype(int)
    base["tomorrow_is_holiday"] = base["tomorrow_is_weekend"]
    base["academic_event"] = 0
    base["tomorrow_academic_event"] = base.groupby("plu_code", dropna=False)["academic_event"].shift(-1).fillna(0).astype(int)
    base["weekday_to_weekend"] = ((base["is_holiday"] == 0) & (base["tomorrow_is_weekend"] == 1)).astype(int)
    base["weekend_to_weekday"] = ((base["is_holiday"] == 1) & (base["tomorrow_is_weekend"] == 0)).astype(int)
    base["building_headcount"] = 0
    base["safety_stock"] = 0
    base["current_stock"] = 0

    base["target_date"] = base["date"] + pd.Timedelta(days=1)
    computed_target = g.shift(-1)
    if "target_sales" in base.columns:
        mismatch = (~base["target_sales"].isna()) & (base["target_sales"].astype(float) != computed_target.astype(float))
        if mismatch.any():
            raise ValueError(f"target_sales mismatch against next-day sales: rows={int(mismatch.sum())}")
    base["target_sales"] = computed_target
    return base


def split_train_valid(df: pd.DataFrame, train_start: str, train_end: str, valid_start: str, valid_end: str) -> SplitData:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    train = d[(d["date"] >= pd.Timestamp(train_start)) & (d["date"] <= pd.Timestamp(train_end))].copy()
    valid = d[(d["date"] >= pd.Timestamp(valid_start)) & (d["date"] <= pd.Timestamp(valid_end))].copy()
    train = train.dropna(subset=["target_sales"])
    valid = valid.dropna(subset=["target_sales"])
    return SplitData(train=train, valid=valid)


def build_model() -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), NUMERIC_COLUMNS),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
        ]
    )
    rf = RandomForestRegressor(
        n_estimators=500,
        max_depth=16,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features="sqrt",
        n_jobs=1,
        random_state=42,
    )
    return Pipeline([("preprocess", pre), ("model", rf)])


def train_and_eval(df: pd.DataFrame, split: SplitData) -> Tuple[Pipeline, Dict[str, float], Dict[str, float]]:
    model = build_model()
    x_train = split.train[FEATURE_COLUMNS]
    y_train = split.train["target_sales"].to_numpy(dtype=float)
    x_valid = split.valid[FEATURE_COLUMNS]
    y_valid = split.valid["target_sales"].to_numpy(dtype=float)

    model.fit(x_train, y_train)
    pred_rf = model.predict(x_valid)
    pred_naive = split.valid["lag_1"].fillna(0.0).to_numpy(dtype=float)
    rf_metrics = compute_metrics(y_valid, pred_rf)
    naive_metrics = compute_metrics(y_valid, pred_naive)
    return model, rf_metrics, naive_metrics


def save_model(model: Pipeline, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path) -> Pipeline:
    return joblib.load(path)


def infer_for_date(df: pd.DataFrame, model: Pipeline, inference_date: str) -> pd.DataFrame:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    target = pd.Timestamp(inference_date)
    day_df = d[d["date"] == target].copy()
    if day_df.empty:
        return day_df
    day_df["pred_raw"] = model.predict(day_df[FEATURE_COLUMNS])
    day_df["predicted_sales"] = np.maximum(0, np.rint(day_df["pred_raw"])).astype(int)
    day_df["recommended_order"] = np.maximum(
        0,
        np.ceil(day_df["predicted_sales"] + day_df["safety_stock"].fillna(0) - day_df["current_stock"].fillna(0)),
    ).astype(int)
    day_df["confidence_score"] = 0.5
    return day_df
