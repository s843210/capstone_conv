from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder


FEATURES = [
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
CAT = ["category_l", "category_m"]
NUM = [c for c in FEATURES if c not in CAT]


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.abs(y_true).sum()
    if denom == 0:
        return float("nan")
    return float(np.abs(y_true - y_pred).sum() / denom)


def bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(y_pred - y_true))


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "wape": wape(y_true, y_pred),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "bias": bias(y_true, y_pred),
    }


def build_supervised(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    if "category_l" not in d.columns:
        d["category_l"] = d["category"]
    if "category_m" not in d.columns:
        d["category_m"] = d["category"]
    d = d.sort_values(["plu_code", "date"]).reset_index(drop=True)
    d["target_date"] = d["date"] + pd.Timedelta(days=1)
    d["tomorrow_day_of_week"] = (d["day_of_week"] + 1) % 7
    d["tomorrow_is_weekend"] = (d["tomorrow_day_of_week"] >= 5).astype(int)
    if "is_holiday" in d.columns:
        d["tomorrow_is_holiday"] = d.groupby("plu_code", dropna=False)["is_holiday"].shift(-1).fillna(0).astype(int)
    else:
        d["tomorrow_is_holiday"] = d["tomorrow_is_weekend"]
    if "academic_event" in d.columns:
        d["tomorrow_academic_event"] = d.groupby("plu_code", dropna=False)["academic_event"].shift(-1).fillna(0).astype(int)
    else:
        d["tomorrow_academic_event"] = 0
    d["weekday_to_weekend"] = ((d["is_holiday"] == 0) & (d["tomorrow_is_weekend"] == 1)).astype(int)
    d["weekend_to_weekday"] = ((d["is_holiday"] == 1) & (d["tomorrow_is_weekend"] == 0)).astype(int)

    if "sales" not in d.columns:
        raise ValueError("target_sales alignment requires sales column.")
    computed_target = d.groupby("plu_code", dropna=False)["sales"].shift(-1)
    if "target_sales" in d.columns:
        mismatch = (~d["target_sales"].isna()) & (d["target_sales"].astype(float) != computed_target.astype(float))
        if mismatch.any():
            raise ValueError(f"target_sales mismatch against next-day sales: rows={int(mismatch.sum())}")
    d["target_sales"] = computed_target
    d = d.dropna(subset=["target_sales"]).copy()
    return d


def build_model(n_jobs: int = -1) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUM),
            ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CAT),
        ]
    )
    rf = RandomForestRegressor(
        n_estimators=500,
        max_depth=16,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features="sqrt",
        n_jobs=n_jobs,
        random_state=42,
    )
    return Pipeline([("preprocess", pre), ("model", rf)])


def confidence_from_forest(pipe: Pipeline, x_df: pd.DataFrame) -> np.ndarray:
    x_trans = pipe.named_steps["preprocess"].transform(x_df)
    model: RandomForestRegressor = pipe.named_steps["model"]
    tree_preds = np.array([est.predict(x_trans) for est in model.estimators_])
    mu = tree_preds.mean(axis=0)
    sd = tree_preds.std(axis=0)
    conf = np.clip(1 - (sd / (mu + 1.0)), 0, 1)
    return conf


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-path", required=True, help="csv or xlsx")
    p.add_argument("--train-start", default="2025-05-01")
    p.add_argument("--train-end", default="2025-05-20")
    p.add_argument("--test-start", default="2025-05-21")
    p.add_argument("--test-end", default="2025-05-30")
    p.add_argument("--model-out", default="models/rf_v4.pkl")
    p.add_argument("--report-out", default="reports/v4_report.json")
    p.add_argument("--pred-out", default="reports/v4_test_predictions.csv")
    args = p.parse_args()

    in_path = Path(args.input_path)
    if in_path.suffix.lower() in (".xlsx", ".xls"):
        raw = pd.read_excel(in_path)
    else:
        raw = pd.read_csv(in_path, encoding="utf-8-sig")
    sup = build_supervised(raw)

    train = sup[(sup["date"] >= args.train_start) & (sup["date"] <= args.train_end)].copy()
    test = sup[(sup["date"] >= args.test_start) & (sup["date"] <= args.test_end)].copy()
    if train.empty or test.empty:
        raise ValueError("train/test split produced empty frame.")

    x_train = train[FEATURES]
    y_train = train["target_sales"].to_numpy(dtype=float)
    x_test = test[FEATURES]
    y_test = test["target_sales"].to_numpy(dtype=float)

    model = build_model(n_jobs=-1)
    try:
        model.fit(x_train, y_train)
    except PermissionError:
        model = build_model(n_jobs=1)
        model.fit(x_train, y_train)

    pred_rf = model.predict(x_test)
    pred_naive = test["lag_1"].to_numpy(dtype=float)

    conf = confidence_from_forest(model, x_test)
    pred_df = test[["date", "target_date", "plu_code", "product_name", "category_l", "category_m"]].copy()
    pred_df["actual_sales"] = y_test
    pred_df["predicted_sales"] = np.maximum(0, np.rint(pred_rf))
    pred_df["naive_pred"] = np.maximum(0, np.rint(pred_naive))
    pred_df["confidence_score"] = conf
    pred_df["abs_error"] = np.abs(pred_df["predicted_sales"] - pred_df["actual_sales"])

    overall = {
        "rf": metrics(y_test, pred_rf),
        "naive_lag1": metrics(y_test, pred_naive),
        "rows": int(len(test)),
        "train_rows": int(len(train)),
    }

    by_cat = []
    for cat, grp in pred_df.groupby("category_m", dropna=False):
        y = grp["actual_sales"].to_numpy(dtype=float)
        r = grp["predicted_sales"].to_numpy(dtype=float)
        n = grp["naive_pred"].to_numpy(dtype=float)
        by_cat.append({"category_m": str(cat), "count": int(len(grp)), "rf": metrics(y, r), "naive_lag1": metrics(y, n)})

    report = {"overall": overall, "by_category": by_cat}
    Path(args.model_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.pred_out).parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, args.model_out)
    Path(args.report_out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pred_df.to_csv(args.pred_out, index=False, encoding="utf-8-sig")

    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    print(f"saved model -> {args.model_out}")
    print(f"saved report -> {args.report_out}")
    print(f"saved preds  -> {args.pred_out}")


if __name__ == "__main__":
    main()
