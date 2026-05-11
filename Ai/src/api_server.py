from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import joblib
import pandas as pd
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[1]
RECOMMENDATION_CSV = BASE_DIR / "outputs" / "reports" / "order_recommendation_monthly_v2_final.csv"
PREDICTION_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction_monthly_v2_final.csv"
TRAIN_RESULT_JSON = BASE_DIR / "outputs" / "reports" / "random_forest_monthly_v2_result.json"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_monthly_v2_model.pkl"

MODEL_NAME = "random_forest_monthly_v2"
UNCLASSIFIED_CATEGORY = "미분류"
DB_PREDICTION_SOURCE = "db"


class RecommendationPolicy(BaseModel):
    exclude_uncategorized: bool = True
    require_sales_history: bool = True
    require_current_stock: bool = True
    only_positive_recommendations: bool = False


class PredictRequest(BaseModel):
    target_date: date | None = None
    mode: Literal["csv", "db"] = "db"
    persist_to_spring: bool = False
    recommendation_policy: RecommendationPolicy = Field(default_factory=RecommendationPolicy)


class TrainRequest(BaseModel):
    mode: Literal["csv"] = "csv"
    force: bool = False


def _run_id(kind: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{MODEL_NAME}-{kind}-{uuid.uuid4().hex[:8]}"


def _run_pipeline(step: str) -> tuple[float, str]:
    started = time.time()
    result = subprocess.run(
        [sys.executable, "run_pipeline.py", "--step", step],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - started
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if result.returncode != 0:
        raise RuntimeError(output.strip() or f"Pipeline step failed: {step}")
    return elapsed, output


def _load_env_files() -> None:
    for path in [BASE_DIR.parent / ".env", BASE_DIR.parent / "backend" / "conv" / ".env"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _db_connection():
    _load_env_files()
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campus_store"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def _default_target_date(df: pd.DataFrame) -> date:
    if "predict_date" not in df.columns or df.empty:
        return date.today() + timedelta(days=1)
    parsed = pd.to_datetime(df["predict_date"], errors="coerce").dropna()
    if parsed.empty:
        return date.today() + timedelta(days=1)
    return parsed.max().date()


def _read_recommendations() -> pd.DataFrame:
    if not RECOMMENDATION_CSV.exists():
        raise FileNotFoundError(f"Recommendation CSV not found: {RECOMMENDATION_CSV}")

    df = pd.read_csv(RECOMMENDATION_CSV, low_memory=False)
    required = {
        "predict_date",
        "plu_code",
        "product_name",
        "product_category",
        "predicted_sales_qty",
        "recommended_order_qty",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"Recommendation CSV is missing columns: {missing}")
    return df


def _latest_sales_date_from_db() -> date:
    with _db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT max(sales_date) FROM daily_sales")
            row = cur.fetchone()
    if not row or row[0] is None:
        raise ValueError("daily_sales is empty; DB predict cannot run.")
    return row[0]


def _db_base_date(target: date | None) -> tuple[date, date]:
    if target is None:
        base = _latest_sales_date_from_db()
        return base, base + timedelta(days=1)
    return target - timedelta(days=1), target


def _read_db_feature_source(base_date: date, policy: RecommendationPolicy) -> pd.DataFrame:
    active_filter = "AND p.is_active = true" if policy.require_current_stock else ""
    category_filter = "AND COALESCE(NULLIF(p.category, ''), '미분류') <> '미분류'" if policy.exclude_uncategorized else ""
    sql = f"""
        SELECT
            d.sales_date AS date,
            d.plu_code,
            COALESCE(NULLIF(p.name, ''), d.plu_code) AS product_name,
            COALESCE(NULLIF(p.category, ''), '미분류') AS product_category,
            d.sales_qty,
            COALESCE(c.avg_temp_c, 0) AS avg_temp,
            COALESCE(c.precipitation_mm, 0) AS rainfall,
            COALESCE(c.is_vacation, 0) AS is_vacation,
            COALESCE(c.class_count, 0) AS class_count,
            COALESCE(c.monday_class_count, 0) AS monday_class_count,
            COALESCE(c.tuesday_class_count, 0) AS tuesday_class_count,
            COALESCE(c.wednesday_class_count, 0) AS wednesday_class_count,
            COALESCE(c.thursday_class_count, 0) AS thursday_class_count,
            COALESCE(c.friday_class_count, 0) AS friday_class_count,
            COALESCE(p.current_stock, 0) AS current_stock,
            COALESCE(p.is_active, false) AS is_active
        FROM daily_sales d
        JOIN product p ON p.plu_code = d.plu_code
        LEFT JOIN daily_context c ON c.target_date = d.sales_date
        WHERE d.sales_date <= %(base_date)s
          {active_filter}
          {category_filter}
        ORDER BY d.plu_code, d.sales_date
    """
    with _db_connection() as conn:
        df = pd.read_sql_query(sql, conn, params={"base_date": base_date})
    if df.empty:
        raise ValueError(f"No DB sales rows found for base_date <= {base_date}")
    return df


def _build_monthly_v2_features_from_db(source: pd.DataFrame, base_date: date) -> pd.DataFrame:
    df = source.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce")
    for col in [
        "class_count",
        "monday_class_count",
        "tuesday_class_count",
        "wednesday_class_count",
        "thursday_class_count",
        "friday_class_count",
        "avg_temp",
        "rainfall",
        "is_vacation",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df[df["date"].notna()].copy()
    df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    grouped = df.groupby("plu_code", group_keys=False)
    df["sales_lag_1"] = grouped["sales_qty"].shift(1)
    df["sales_lag_7"] = grouped["sales_qty"].shift(7)
    shifted = grouped["sales_qty"].shift(1)
    df["rolling_mean_7"] = shifted.groupby(df["plu_code"]).transform(
        lambda s: s.rolling(window=7, min_periods=7).mean()
    )
    df["rolling_mean_14"] = shifted.groupby(df["plu_code"]).transform(
        lambda s: s.rolling(window=14, min_periods=14).mean()
    )
    df["rolling_mean_28"] = shifted.groupby(df["plu_code"]).transform(
        lambda s: s.rolling(window=28, min_periods=28).mean()
    )

    df["is_rainy"] = (df["rainfall"] > 0).astype(int)
    df["is_hot"] = (df["avg_temp"] >= 27).astype(int)
    df["is_cold"] = (df["avg_temp"] <= 5).astype(int)
    df["is_semester"] = (df["is_vacation"] != 1).astype(int)

    return df[df["date"] == pd.Timestamp(base_date)].copy().reset_index(drop=True)


def _to_recommended_qty(predicted_sales: float) -> int:
    if pd.isna(predicted_sales) or predicted_sales <= 0:
        return 0
    qty = int(math.ceil(float(predicted_sales) * 1.2))
    return 0 if qty < 2 else qty


def _encode_features(features: pd.DataFrame, bundle: dict[str, Any]) -> tuple[pd.DataFrame, pd.Series]:
    feature_cols = bundle.get("feature_cols", bundle.get("feature_columns"))
    categorical_cols = bundle.get("categorical_cols", bundle.get("categorical_columns", []))
    label_maps = bundle.get("label_maps")
    label_encoders = bundle.get("label_encoders")
    if feature_cols is None:
        raise KeyError("Model bundle does not contain feature_cols/feature_columns.")

    missing = [col for col in feature_cols if col not in features.columns]
    if missing:
        raise KeyError(f"Missing DB feature columns: {missing}")

    X = features[feature_cols].copy()
    for col in categorical_cols:
        if col not in X.columns:
            continue
        if label_maps is not None and col in label_maps:
            mapping = label_maps[col]
            X[col] = X[col].astype(str).map(mapping).fillna(-1).astype(int)
        elif label_encoders is not None and col in label_encoders:
            encoder = label_encoders[col]
            mapping = {cls: idx for idx, cls in enumerate(encoder.classes_)}
            X[col] = X[col].astype(str).map(mapping).fillna(-1).astype(int)
        else:
            X[col] = X[col].astype("category").cat.codes

    for col in X.columns:
        if col in categorical_cols:
            continue
        X[col] = pd.to_numeric(X[col], errors="coerce")

    valid_mask = X.notna().all(axis=1)
    return X[valid_mask].copy(), valid_mask


def _write_db_prediction_outputs(out_df: pd.DataFrame) -> None:
    PREDICTION_CSV.parent.mkdir(parents=True, exist_ok=True)
    RECOMMENDATION_CSV.parent.mkdir(parents=True, exist_ok=True)
    pred_cols = [
        "base_date",
        "predict_date",
        "plu_code",
        "product_name",
        "product_category",
        "predicted_sales_qty",
    ]
    rec_cols = pred_cols + ["recommended_order_qty"]
    out_df[pred_cols].to_csv(PREDICTION_CSV, index=False, encoding="utf-8-sig")
    out_df[rec_cols].to_csv(RECOMMENDATION_CSV, index=False, encoding="utf-8-sig")


def _predict_from_db(target: date | None, policy: RecommendationPolicy) -> tuple[date, pd.DataFrame, dict[str, Any]]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    base_date, predict_date = _db_base_date(target)
    source = _read_db_feature_source(base_date, policy)
    latest_features = _build_monthly_v2_features_from_db(source, base_date)
    if latest_features.empty:
        raise ValueError(f"No feature rows available for base_date={base_date}")

    bundle = joblib.load(MODEL_PATH)
    X, valid_mask = _encode_features(latest_features, bundle)
    valid_features = latest_features.loc[valid_mask].copy()
    if X.empty:
        raise ValueError(f"No valid DB feature rows after NaN filtering for base_date={base_date}")

    preds = pd.Series(bundle["model"].predict(X), index=valid_features.index).clip(lower=0)
    out_df = pd.DataFrame(
        {
            "base_date": base_date.isoformat(),
            "predict_date": predict_date.isoformat(),
            "plu_code": valid_features["plu_code"].astype(str).values,
            "product_name": valid_features["product_name"].astype(str).values,
            "product_category": valid_features["product_category"].astype(str).values,
            "predicted_sales_qty": preds.astype(float).values,
        }
    )
    out_df["recommended_order_qty"] = out_df["predicted_sales_qty"].map(_to_recommended_qty).astype(int)
    out_df = _apply_policy(out_df, policy)
    _write_db_prediction_outputs(out_df)

    diagnostics = {
        "source": DB_PREDICTION_SOURCE,
        "base_date": base_date.isoformat(),
        "source_rows": int(len(source)),
        "candidate_rows_on_base_date": int(len(latest_features)),
        "valid_feature_rows": int(len(valid_features)),
        "excluded_rows_due_to_missing_features": int(len(latest_features) - len(valid_features)),
    }
    return predict_date, out_df, diagnostics


def _apply_policy(df: pd.DataFrame, policy: RecommendationPolicy) -> pd.DataFrame:
    out = df.copy()
    if policy.exclude_uncategorized and "product_category" in out.columns:
        out = out[out["product_category"].fillna("").astype(str) != UNCLASSIFIED_CATEGORY]
    if policy.only_positive_recommendations:
        recommended = pd.to_numeric(out["recommended_order_qty"], errors="coerce").fillna(0)
        out = out[recommended > 0]
    return out


def _to_results(df: pd.DataFrame, target: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        predicted_sales = pd.to_numeric(row["predicted_sales_qty"], errors="coerce")
        recommended_order = pd.to_numeric(row["recommended_order_qty"], errors="coerce")
        rows.append(
            {
                "plu_code": str(row["plu_code"]),
                "product_name": "" if pd.isna(row["product_name"]) else str(row["product_name"]),
                "product_category": "" if pd.isna(row["product_category"]) else str(row["product_category"]),
                "target_date": target.isoformat(),
                "predicted_sales": 0.0 if pd.isna(predicted_sales) else float(predicted_sales),
                "recommended_order": 0 if pd.isna(recommended_order) else int(recommended_order),
                "confidence_score": None,
            }
        )
    return rows


def _to_spring_payload(target: date, results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in results:
        category = item["product_category"] or UNCLASSIFIED_CATEGORY
        bucket = grouped.setdefault(
            category,
            {
                "categoryName": category,
                "totalRecommendedOrder": 0,
                "aiMessage": "monthly_v2 recommendation",
                "products": [],
            },
        )
        recommended_order = int(item["recommended_order"])
        bucket["totalRecommendedOrder"] += recommended_order
        bucket["products"].append(
            {
                "pluCode": item["plu_code"],
                "predictedSales": int(round(float(item["predicted_sales"]))),
                "recommendedOrder": recommended_order,
                "confidenceScore": item["confidence_score"],
            }
        )

    return {
        "targetDate": target.isoformat(),
        "categories": list(grouped.values()),
    }


app = FastAPI(title="Campus Store AI API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_name": MODEL_NAME}


@app.post("/ai/predict")
@app.post("/ai/monthly-v2/predict")
def predict(request: PredictRequest) -> dict[str, Any]:
    run_id = _run_id("predict")
    started_at = datetime.now()
    try:
        started = time.time()
        pipeline_output = ""
        diagnostics: dict[str, Any] = {}

        if request.mode == "db":
            target, filtered, diagnostics = _predict_from_db(
                request.target_date,
                request.recommendation_policy,
            )
            elapsed = time.time() - started
        else:
            elapsed, pipeline_output = _run_pipeline("predict")
            df = _read_recommendations()
            target = request.target_date or _default_target_date(df)

            df["predict_date"] = pd.to_datetime(df["predict_date"], errors="coerce").dt.date
            filtered = df[df["predict_date"] == target].copy()
            filtered = _apply_policy(filtered, request.recommendation_policy)

        results = _to_results(filtered, target)

        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "model_name": MODEL_NAME,
            "target_date": target.isoformat(),
            "started_at": started_at.isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "duration_seconds": round(elapsed, 4),
            "row_count": len(results),
            "csv_outputs": {
                "prediction_csv": str(PREDICTION_CSV),
                "recommendation_csv": str(RECOMMENDATION_CSV),
            },
            "policy": request.recommendation_policy.model_dump(),
            "mode": request.mode,
            "diagnostics": diagnostics,
            "results": results,
            "spring_payload": _to_spring_payload(target, results),
            "pipeline_output_tail": pipeline_output[-4000:],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "run_id": run_id,
                "status": "FAILED",
                "model_name": MODEL_NAME,
                "target_date": request.target_date.isoformat() if request.target_date else None,
                "error": str(exc),
            },
        ) from exc


@app.post("/ai/train")
@app.post("/ai/monthly-v2/train")
def train(request: TrainRequest) -> dict[str, Any]:
    run_id = _run_id("train")
    started_at = datetime.now()
    try:
        elapsed, pipeline_output = _run_pipeline("train")
        metrics: dict[str, Any] = {}
        if TRAIN_RESULT_JSON.exists():
            with TRAIN_RESULT_JSON.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            metrics = payload.get("metrics", {})

        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "model_name": MODEL_NAME,
            "model_path": str(MODEL_PATH),
            "started_at": started_at.isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "duration_seconds": round(elapsed, 4),
            "metrics": metrics,
            "pipeline_output_tail": pipeline_output[-4000:],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "run_id": run_id,
                "status": "FAILED",
                "model_name": MODEL_NAME,
                "error": str(exc),
            },
        ) from exc
