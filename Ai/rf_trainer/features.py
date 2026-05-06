from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


ID_COLUMNS = ["date", "target_date", "plu_code", "product_name"]
CATEGORICAL_COLUMNS = ["category_l", "category_m"]
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
LEAKAGE_COLUMNS = ["sales", "target_sales", "safety_stock", "plu_code", "date", "product_name"]
TARGET_COLUMN = "target_sales"
REQUIRED_BASE_COLUMNS = ["date", "plu_code", "sales", "product_name"] + FEATURE_COLUMNS


@dataclass
class SupervisedData:
    frame: pd.DataFrame
    x: pd.DataFrame
    y: pd.Series


def ensure_columns(df: pd.DataFrame, required: List[str], context: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{context}: missing columns={missing}")


def build_supervised_frame(df: pd.DataFrame, exact_only: bool = True) -> pd.DataFrame:
    ensure_columns(df, REQUIRED_BASE_COLUMNS, "build_supervised_frame")
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    if exact_only and "match_type" in out.columns:
        out = out[out["match_type"] == "exact"].copy()

    out = out.sort_values(["plu_code", "date"], ascending=[True, True]).reset_index(drop=True)
    out["target_date"] = out["date"] + pd.Timedelta(days=1)
    computed_target = out.groupby("plu_code", dropna=False)["sales"].shift(-1)
    if TARGET_COLUMN in out.columns:
        mismatch = (~out[TARGET_COLUMN].isna()) & (out[TARGET_COLUMN].astype(float) != computed_target.astype(float))
        if mismatch.any():
            raise ValueError(
                f"target alignment mismatch: provided {TARGET_COLUMN} does not match next-day sales for "
                f"{int(mismatch.sum())} rows"
            )
    out[TARGET_COLUMN] = computed_target
    out = out.dropna(subset=[TARGET_COLUMN]).copy()
    return out


def build_training_xy(supervised: pd.DataFrame) -> SupervisedData:
    ensure_columns(supervised, FEATURE_COLUMNS + [TARGET_COLUMN], "build_training_xy")
    x = supervised[FEATURE_COLUMNS].copy()
    y = supervised[TARGET_COLUMN].astype(float).copy()
    return SupervisedData(frame=supervised, x=x, y=y)


def validate_key_uniqueness(df: pd.DataFrame) -> None:
    ensure_columns(df, ["target_date", "plu_code"], "validate_key_uniqueness")
    dup = df.duplicated(subset=["target_date", "plu_code"], keep=False)
    if dup.any():
        sample = df.loc[dup, ["target_date", "plu_code"]].head(10)
        raise ValueError(f"duplicate keys found for target_date+plu_code, sample=\n{sample}")
