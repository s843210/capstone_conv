from __future__ import annotations

import argparse
import json
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
    denom = float(np.abs(y_true).sum())
    if denom == 0:
        return float("nan")
    return float(np.abs(y_true - y_pred).sum() / denom)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(y_pred - y_true))


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    w = wape(y_true, y_pred)
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "wape": w,
        "acc_1_minus_wape": 1.0 - w if not np.isnan(w) else float("nan"),
        "bias": bias(y_true, y_pred),
    }


def load_data(path: Path, drop_negative_sales: bool = True) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])

    if drop_negative_sales and "sales" in df.columns:
        df = df[df["sales"] >= 0].copy()
    return df


def _add_tomorrow_lookup(df: pd.DataFrame, src_col: str, new_col: str) -> pd.DataFrame:
    if src_col not in df.columns:
        return df
    cal = (
        df[["date", src_col]]
        .drop_duplicates(subset=["date"])
        .assign(_lookup_date=lambda x: x["date"] - pd.Timedelta(days=1))
        .rename(columns={src_col: new_col})[["_lookup_date", new_col]]
    )
    out = df.merge(cal, left_on="date", right_on="_lookup_date", how="left").drop(columns=["_lookup_date"])
    return out


def build_supervised(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "plu_code" not in d.columns:
        raise ValueError("plu_code is required.")
    if "sales" not in d.columns:
        raise ValueError("sales is required.")
    if "category_l" not in d.columns:
        d["category_l"] = d.get("category_m", "unknown")
    if "category_m" not in d.columns:
        d["category_m"] = d.get("category_l", "unknown")

    d = d.sort_values(["plu_code", "date"]).reset_index(drop=True)
    g = d.groupby("plu_code", dropna=False)["sales"]
    d["lag_1"] = d.get("lag_1", g.shift(1))
    d["lag_3"] = d.get("lag_3", g.shift(3))
    d["lag_7"] = d.get("lag_7", g.shift(7))
    d["rolling_7_mean"] = d.get("rolling_7_mean", g.shift(1).rolling(7, min_periods=1).mean())
    d["rolling_7_std"] = d.get("rolling_7_std", g.shift(1).rolling(7, min_periods=1).std())

    d["day_of_week"] = d.get("day_of_week", d["date"].dt.dayofweek)
    d["month"] = d.get("month", d["date"].dt.month)
    d["is_holiday"] = d.get("is_holiday", (d["day_of_week"] >= 5).astype(int))
    d["academic_event"] = d.get("academic_event", 0)
    d["building_headcount"] = d.get("building_headcount", 0)
    d["safety_stock"] = d.get("safety_stock", 0)

    d["tomorrow_day_of_week"] = (d["day_of_week"] + 1) % 7
    d["tomorrow_is_weekend"] = (d["tomorrow_day_of_week"] >= 5).astype(int)
    d = _add_tomorrow_lookup(d, "is_holiday", "tomorrow_is_holiday")
    d = _add_tomorrow_lookup(d, "academic_event", "tomorrow_academic_event")
    d["tomorrow_is_holiday"] = d["tomorrow_is_holiday"].fillna(d["tomorrow_is_weekend"]).astype(int)
    d["tomorrow_academic_event"] = d["tomorrow_academic_event"].fillna(d["academic_event"]).astype(int)
    d["weekday_to_weekend"] = d["day_of_week"].isin([4, 5]).astype(int)
    d["weekend_to_weekday"] = (d["day_of_week"] == 6).astype(int)

    d["target_date"] = d["date"] + pd.Timedelta(days=1)
    computed_target = g.shift(-1)
    if "target_sales" in d.columns:
        mismatch = (~d["target_sales"].isna()) & (d["target_sales"].astype(float) != computed_target.astype(float))
        if mismatch.any():
            raise ValueError(f"target_sales mismatch against next-day sales: rows={int(mismatch.sum())}")
    d["target_sales"] = computed_target

    fill_zero_cols = [
        "lag_1",
        "lag_3",
        "lag_7",
        "rolling_7_mean",
        "rolling_7_std",
        "building_headcount",
        "safety_stock",
    ]
    for c in fill_zero_cols:
        d[c] = d[c].fillna(0)

    d = d.dropna(subset=["target_sales"]).reset_index(drop=True)
    return d


def split_3way(df: pd.DataFrame, train_start: str, train_end: str, valid_start: str, valid_end: str, test_start: str, test_end: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tr = df[(df["date"] >= train_start) & (df["date"] <= train_end)].copy()
    va = df[(df["date"] >= valid_start) & (df["date"] <= valid_end)].copy()
    te = df[(df["date"] >= test_start) & (df["date"] <= test_end)].copy()
    if tr.empty or va.empty or te.empty:
        raise ValueError("train/valid/test split produced empty frame.")
    return tr, va, te


def build_rf(n_jobs: int = -1) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
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


def tune_blend_weight(y_valid: np.ndarray, pred_rf_valid: np.ndarray, pred_base_valid: np.ndarray) -> float:
    best_w = 1.0
    best_mae = float("inf")
    for w in np.linspace(0.0, 1.0, 21):
        pred = w * pred_rf_valid + (1.0 - w) * pred_base_valid
        score = mae(y_valid, pred)
        if score < best_mae:
            best_mae = score
            best_w = float(w)
    return best_w


def decompose_cases(df: pd.DataFrame, y_pred: np.ndarray) -> pd.DataFrame:
    work = df.copy()
    work["y_pred"] = y_pred
    work["abs_err"] = (work["target_sales"] - work["y_pred"]).abs()
    c1 = (work["sales"] == 0) & (work["target_sales"] == 0)
    c2 = (work["sales"] == 0) & (work["target_sales"] > 0)
    c3 = (work["sales"] > 0) & (work["target_sales"] == 0)
    c4 = (work["sales"] > 0) & (work["target_sales"] > 0)
    work["case"] = np.select([c1, c2, c3, c4], ["Case1_0_0", "Case2_0_pos", "Case3_pos_0", "Case4_pos_pos"], default="unknown")
    total_err = float(work["abs_err"].sum())
    rows = []
    for case_name in ["Case1_0_0", "Case2_0_pos", "Case3_pos_0", "Case4_pos_pos"]:
        grp = work[work["case"] == case_name]
        case_err = float(grp["abs_err"].sum())
        rows.append(
            {
                "case": case_name,
                "n": int(len(grp)),
                "ratio": float(len(grp) / len(work)),
                "abs_err_sum": case_err,
                "err_contribution": float(case_err / total_err) if total_err > 0 else 0.0,
                "mae": float(grp["abs_err"].mean()) if len(grp) else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-path", required=True)
    p.add_argument("--train-start", required=True)
    p.add_argument("--train-end", required=True)
    p.add_argument("--valid-start", required=True)
    p.add_argument("--valid-end", required=True)
    p.add_argument("--test-start", required=True)
    p.add_argument("--test-end", required=True)
    p.add_argument("--model-out", default="models/rf_hybrid_tuned.pkl")
    p.add_argument("--report-out", default="reports/hybrid_tuned_report.json")
    p.add_argument("--pred-out", default="reports/hybrid_tuned_predictions.csv")
    p.add_argument("--comparison-out", default="reports/hybrid_tuned_comparison.csv")
    p.add_argument("--drop-negative-sales", action="store_true")
    args = p.parse_args()

    raw = load_data(Path(args.input_path), drop_negative_sales=args.drop_negative_sales)
    sup = build_supervised(raw)
    train, valid, test = split_3way(
        sup,
        args.train_start,
        args.train_end,
        args.valid_start,
        args.valid_end,
        args.test_start,
        args.test_end,
    )

    x_train = train[FEATURES]
    y_train = train["target_sales"].to_numpy(dtype=float)
    x_valid = valid[FEATURES]
    y_valid = valid["target_sales"].to_numpy(dtype=float)
    x_test = test[FEATURES]
    y_test = test["target_sales"].to_numpy(dtype=float)

    model = build_rf(n_jobs=-1)
    try:
        model.fit(x_train, y_train)
    except PermissionError:
        model = build_rf(n_jobs=1)
        model.fit(x_train, y_train)
    pred_rf_valid = model.predict(x_valid)
    pred_rf_test = model.predict(x_test)

    pred_base_valid = valid["sales"].to_numpy(dtype=float)
    pred_base_test = test["sales"].to_numpy(dtype=float)

    blend_w = tune_blend_weight(y_valid, pred_rf_valid, pred_base_valid)
    pred_blend_test = blend_w * pred_rf_test + (1.0 - blend_w) * pred_base_test

    base_m = metrics(y_test, pred_base_test)
    rf_m = metrics(y_test, pred_rf_test)
    blend_m = metrics(y_test, pred_blend_test)

    if blend_m["mae"] < rf_m["mae"] and blend_m["wape"] < rf_m["wape"]:
        final_name = "rf_baseline_blend"
        final_pred = pred_blend_test
        final_m = blend_m
    else:
        final_name = "rf_only"
        final_pred = pred_rf_test
        final_m = rf_m

    pred_df = test[["date", "target_date", "plu_code", "product_name", "category_l", "category_m", "sales", "target_sales"]].copy()
    pred_df["pred_baseline"] = np.maximum(0, np.rint(pred_base_test))
    pred_df["pred_rf"] = np.maximum(0, np.rint(pred_rf_test))
    pred_df["pred_blend"] = np.maximum(0, np.rint(pred_blend_test))
    pred_df["pred_final"] = np.maximum(0, np.rint(final_pred))
    pred_df["abs_err_final"] = np.abs(pred_df["pred_final"] - pred_df["target_sales"])

    cmp_df = pd.DataFrame(
        [
            {"model": "baseline_sales", **base_m},
            {"model": "rf", **rf_m},
            {"model": "rf_blend", **blend_m},
            {"model": f"selected::{final_name}", **final_m},
        ]
    )
    cmp_df["d_mae_vs_baseline"] = cmp_df["mae"] - base_m["mae"]
    cmp_df["d_wape_vs_baseline"] = cmp_df["wape"] - base_m["wape"]
    cmp_df["adoptable_vs_baseline"] = (cmp_df["mae"] < base_m["mae"]) & (cmp_df["wape"] < base_m["wape"])

    report = {
        "rows": {"train": int(len(train)), "valid": int(len(valid)), "test": int(len(test))},
        "date_range": {
            "train": [str(train["date"].min().date()), str(train["date"].max().date())],
            "valid": [str(valid["date"].min().date()), str(valid["date"].max().date())],
            "test": [str(test["date"].min().date()), str(test["date"].max().date())],
        },
        "blend_weight_rf": blend_w,
        "selected_model": final_name,
        "metrics": {"baseline": base_m, "rf": rf_m, "blend": blend_m, "selected": final_m},
        "case_decomposition": {
            "baseline": decompose_cases(test, pred_base_test).to_dict(orient="records"),
            "rf": decompose_cases(test, pred_rf_test).to_dict(orient="records"),
            "selected": decompose_cases(test, final_pred).to_dict(orient="records"),
        },
        "feature_columns": FEATURES,
    }

    model_out = Path(args.model_out)
    report_out = Path(args.report_out)
    pred_out = Path(args.pred_out)
    cmp_out = Path(args.comparison_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    pred_out.parent.mkdir(parents=True, exist_ok=True)
    cmp_out.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_out)
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pred_df.to_csv(pred_out, index=False, encoding="utf-8-sig")
    cmp_df.to_csv(cmp_out, index=False, encoding="utf-8-sig")

    print(json.dumps({"selected_model": final_name, "metrics_selected": final_m, "blend_weight_rf": blend_w}, ensure_ascii=False, indent=2))
    print(f"saved model -> {model_out}")
    print(f"saved report -> {report_out}")
    print(f"saved preds  -> {pred_out}")
    print(f"saved comp   -> {cmp_out}")


if __name__ == "__main__":
    main()
