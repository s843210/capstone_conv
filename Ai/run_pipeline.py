#!/usr/bin/env python
"""Unified entry-point for the demand-forecast pipeline.

Usage::

    python run_pipeline.py --step all          # monthly-v2 full pipeline
    python run_pipeline.py --step preprocess   # monthly data -> model features
    python run_pipeline.py --step train        # train monthly-v2 RandomForest model
    python run_pipeline.py --step predict      # monthly-v2 prediction + order recommendation
"""

from __future__ import annotations

import argparse
import runpy
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _run_script(relative_path: str) -> None:
    script_path = BASE_DIR / relative_path
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    print(f"\n{'-'*60}")
    print(f"  Script: {relative_path}")
    print(f"{'-'*60}")
    runpy.run_path(str(script_path), run_name="__main__")


MONTHLY_PREPROCESS_SCRIPTS = [
    "src/54_convert_monthly_sales_to_daily_filled_v2.py",
    "src/56_clean_monthly_sales_daily_filled_v2.py",
    "src/57_merge_monthly_sales_with_calendar_v2.py",
    "src/58_merge_monthly_sales_with_timetable_v2.py",
    "src/60_rebuild_weather_features_v2.py",
    "src/62_merge_monthly_sales_with_weather_v2.py",
    "src/63_build_model_features_monthly_v2.py",
]

MONTHLY_TRAIN_SCRIPTS = [
    "src/73_train_random_forest_monthly_v2.py",
]

MONTHLY_PREDICT_SCRIPTS = [
    "src/78_make_tomorrow_prediction_monthly_v2_final.py",
    "src/79_make_order_recommendation_monthly_v2_final.py",
]


def _step_monthly_preprocess() -> None:
    for script in MONTHLY_PREPROCESS_SCRIPTS:
        _run_script(script)


def _step_monthly_train() -> None:
    for script in MONTHLY_TRAIN_SCRIPTS:
        _run_script(script)


def _step_monthly_predict() -> None:
    for script in MONTHLY_PREDICT_SCRIPTS:
        _run_script(script)


def _step_monthly_v2() -> None:
    _step_monthly_preprocess()
    _step_monthly_train()
    _step_monthly_predict()


STEPS = {
    "all": _step_monthly_v2,
    "preprocess": _step_monthly_preprocess,
    "train": _step_monthly_train,
    "predict": _step_monthly_predict,
    "monthly-preprocess": _step_monthly_preprocess,
    "monthly-train": _step_monthly_train,
    "monthly-predict": _step_monthly_predict,
    "monthly-v2": _step_monthly_v2,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Demand-forecast pipeline runner")
    parser.add_argument(
        "--step",
        choices=list(STEPS.keys()),
        default="all",
        help="Pipeline step to run (default: all)",
    )
    args = parser.parse_args()
    STEPS[args.step]()

    print("\nDone.")


if __name__ == "__main__":
    main()
