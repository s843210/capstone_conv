"""Central configuration loader.

Reads ``config/config.yaml`` and exposes paths resolved relative to the
project root (``BASE_DIR``).  Falls back to sensible defaults when the
YAML file is missing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


# Project root: one level above ``src/``
BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"


def _load_yaml() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return {}


_CFG = _load_yaml()


# ---------------------------------------------------------------------------
# Helper to resolve a relative path against BASE_DIR
# ---------------------------------------------------------------------------

def _resolve(relative: str) -> Path:
    return BASE_DIR / relative


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

class Paths:
    """All filesystem paths used by the pipeline."""

    # Raw
    SALES_DIR        = _resolve(_CFG.get("paths", {}).get("raw", {}).get("sales_dir", "data/raw/sales"))
    PRODUCT_MASTER_DIR = _resolve(_CFG.get("paths", {}).get("raw", {}).get("product_master_dir", "data/raw/product/product_master/csv_상품분류기준표"))
    CALENDAR_CSV     = _resolve(_CFG.get("paths", {}).get("raw", {}).get("calendar_csv", "data/raw/calendar/academic_calendar_2026.csv"))
    TIMETABLE_2024_2025 = _resolve(_CFG.get("paths", {}).get("raw", {}).get("timetable_2024_2025", "data/raw/timetable/timetable_2024_2025.xlsx"))
    TIMETABLE_2026   = _resolve(_CFG.get("paths", {}).get("raw", {}).get("timetable_2026", "data/raw/timetable/timetable_2026.xlsx"))
    WEATHER_DIR      = _resolve(_CFG.get("paths", {}).get("raw", {}).get("weather_dir", "data/raw/weather"))

    # Processed
    DAILY_SALES_RAW  = _resolve(_CFG.get("paths", {}).get("processed", {}).get("daily_sales_raw", "data/processed/daily_sales_raw_v2.csv"))
    PRODUCT_MASTER   = _resolve(_CFG.get("paths", {}).get("processed", {}).get("product_master", "data/processed/product_master.csv"))
    REPRESENTATIVE_PRODUCT = _resolve(_CFG.get("paths", {}).get("processed", {}).get("representative_product", "data/processed/representative_product_master.csv"))
    SALES_WITH_PRODUCT = _resolve(_CFG.get("paths", {}).get("processed", {}).get("sales_with_product", "data/processed/daily_sales_with_product.csv"))
    SALES_WITH_PRODUCT_IMPROVED = _resolve(_CFG.get("paths", {}).get("processed", {}).get("sales_with_product_improved", "data/processed/daily_sales_with_product_improved.csv"))
    FINAL_SALES      = _resolve(_CFG.get("paths", {}).get("processed", {}).get("final_sales", "data/processed/final_sales_dataset.csv"))
    CALENDAR_FEATURES = _resolve(_CFG.get("paths", {}).get("processed", {}).get("calendar_features", "data/processed/academic_calendar_features.csv"))
    SALES_WITH_CALENDAR = _resolve(_CFG.get("paths", {}).get("processed", {}).get("sales_with_calendar", "data/processed/sales_with_calendar.csv"))
    TIMETABLE_FEATURES = _resolve(_CFG.get("paths", {}).get("processed", {}).get("timetable_features", "data/processed/timetable_features.csv"))
    SALES_WITH_CALENDAR_TIMETABLE = _resolve(_CFG.get("paths", {}).get("processed", {}).get("sales_with_calendar_timetable", "data/processed/sales_with_calendar_timetable.csv"))
    WEATHER_FEATURES = _resolve(_CFG.get("paths", {}).get("processed", {}).get("weather_features", "data/processed/weather_features.csv"))
    SALES_WITH_WEATHER = _resolve(_CFG.get("paths", {}).get("processed", {}).get("sales_with_weather", "data/processed/sales_with_calendar_timetable_weather.csv"))
    MODEL_FEATURES   = _resolve(_CFG.get("paths", {}).get("processed", {}).get("model_features", "data/processed/model_features.csv"))
    MODEL_FEATURES_WEATHER_BINARY = _resolve(_CFG.get("paths", {}).get("processed", {}).get("model_features_weather_binary", "data/processed/model_features_weather_binary.csv"))

    # Models
    MODEL_RF_FAST    = _resolve(os.environ.get("MODEL_PATH", _CFG.get("paths", {}).get("models", {}).get("rf_fast", "outputs/models/random_forest_fast_model.pkl")))
    MODEL_LIGHTGBM   = _resolve(_CFG.get("paths", {}).get("models", {}).get("lightgbm", "outputs/models/lightgbm_model.pkl"))

    # Reports
    REPORTS_DIR      = _resolve(_CFG.get("paths", {}).get("reports_dir", "outputs/reports"))


# ---------------------------------------------------------------------------
# Training parameters
# ---------------------------------------------------------------------------

class Training:
    _t = _CFG.get("training", {})
    TRAIN_START   = _t.get("train_start", "2024-04-02")
    TRAIN_END     = _t.get("train_end", "2025-12-31")
    TEST_START    = _t.get("test_start", "2026-01-01")
    TARGET_COL    = _t.get("target_col", "target_sales")

    RF_PARAMS = _t.get("random_forest", {
        "n_estimators": 100, "max_depth": 20,
        "min_samples_leaf": 3, "random_state": 42,
    })
    LGBM_PARAMS = _t.get("lightgbm", {
        "n_estimators": 500, "learning_rate": 0.05,
        "max_depth": -1, "random_state": 42,
    })


# ---------------------------------------------------------------------------
# Inference parameters
# ---------------------------------------------------------------------------

class Inference:
    _i = _CFG.get("inference", {})
    SAFETY_FACTOR = _i.get("safety_factor", 1.2)

    _g = _i.get("guardrail", {})
    GUARDRAIL_SAFETY_FACTOR = _g.get("safety_factor", 1.05)
    GUARDRAIL_BLEND_ALPHA   = _g.get("blend_alpha", 0.4)
    GUARDRAIL_UPPER_CAP     = _g.get("upper_cap_multiplier", 1.2)
    GUARDRAIL_LOWER_FLOOR   = _g.get("lower_floor", 0.0)


# ---------------------------------------------------------------------------
# Preprocessing constants
# ---------------------------------------------------------------------------

class Preprocessing:
    _p = _CFG.get("preprocessing", {})
    HEADER_KEYWORD    = _p.get("header_keyword", "카테고리/상품")
    EXCEL_EXTENSIONS  = set(_p.get("excel_extensions", [".xlsx", ".xls", ".xlsm"]))
    SUMMARY_PATTERN   = _p.get("summary_pattern", r"(?:합계|총계|계$)")
