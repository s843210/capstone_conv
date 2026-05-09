#!/usr/bin/env python
"""Unified entry-point for the demand-forecast pipeline.

Usage::

    python run_pipeline.py --step all          # full pipeline
    python run_pipeline.py --step ingest       # sales + product merge only
    python run_pipeline.py --step preprocess   # match + final dataset
    python run_pipeline.py --step features     # calendar + timetable + model features
    python run_pipeline.py --step train        # baseline + RF + LGBM + compare
    python run_pipeline.py --step predict      # tomorrow prediction + orders + guardrails
    python run_pipeline.py --step interactive  # interactive product search test
"""

from __future__ import annotations

import argparse
import sys


def _step_ingest() -> None:
    from src.pipeline.ingest import merge_sales_files, merge_product_master
    merge_sales_files()
    merge_product_master()


def _step_preprocess() -> None:
    from src.pipeline.preprocess import match_sales_with_product, build_final_sales_dataset
    match_sales_with_product()
    build_final_sales_dataset()


def _step_features() -> None:
    from src.pipeline.features import (
        build_calendar_features,
        merge_sales_with_calendar,
        build_timetable_features,
        merge_sales_with_timetable,
        build_model_features,
    )
    build_calendar_features()
    merge_sales_with_calendar()
    build_timetable_features()
    merge_sales_with_timetable()
    build_model_features()


def _step_train() -> None:
    from src.pipeline.train import (
        train_baseline,
        train_random_forest,
        train_lightgbm,
        compare_models,
    )
    train_baseline()
    train_random_forest()
    train_lightgbm()
    compare_models()


def _step_predict() -> None:
    from src.pipeline.infer import predict_tomorrow, recommend_orders, apply_guardrails
    predict_tomorrow()
    recommend_orders()
    apply_guardrails()


def _step_interactive() -> None:
    from src.serving.preprocess_for_infer import interactive_test
    interactive_test()


STEPS = {
    "ingest": _step_ingest,
    "preprocess": _step_preprocess,
    "features": _step_features,
    "train": _step_train,
    "predict": _step_predict,
    "interactive": _step_interactive,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Demand-forecast pipeline runner")
    parser.add_argument(
        "--step",
        choices=["all"] + list(STEPS.keys()),
        default="all",
        help="Pipeline step to run (default: all)",
    )
    args = parser.parse_args()

    if args.step == "all":
        ordered = ["ingest", "preprocess", "features", "train", "predict"]
        for name in ordered:
            print(f"\n{'='*60}")
            print(f"  Step: {name}")
            print(f"{'='*60}")
            STEPS[name]()
    else:
        STEPS[args.step]()

    print("\nDone.")


if __name__ == "__main__":
    main()
