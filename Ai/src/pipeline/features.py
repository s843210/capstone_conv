"""Features — build calendar, timetable, and model features.

Consolidates logic from legacy scripts 19, 20, 22, 23, 24.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ..config import Paths
from ..utils.io import safe_read_csv, safe_save_csv
from ..utils.date_parse import parse_date_series
from ..utils.report import write_report


# ===================================================================
# Calendar features  (legacy 19, 20)
# ===================================================================

CALENDAR_FEATURE_COLS = [
    "is_start_semester",
    "is_end_semester",
    "is_exam",
    "is_vacation",
    "is_festival",
    "is_holiday_or_no_class",
]


def build_calendar_features(
    input_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Parse academic calendar and produce binary event flags per day."""
    input_csv = input_csv or Paths.CALENDAR_CSV
    output_csv = output_csv or Paths.CALENDAR_FEATURES

    try:
        df = pd.read_csv(input_csv, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(input_csv, encoding="cp949", low_memory=False)

    if "date" not in df.columns:
        raise KeyError("'date' column not found in calendar file.")

    df["date"] = parse_date_series(df["date"])
    df = df[df["date"].notna()].copy()

    # detect text columns
    text_cols = [c for c in df.columns if c != "date" and (
        df[c].dtype == "object" or str(df[c].dtype).startswith("string")
        or any(k in str(c).lower() for k in ["event", "내용", "일정", "행사", "비고"])
    )]
    if not text_cols:
        text_cols = [c for c in df.columns if c != "date"]

    row_text = (
        df[text_cols].fillna("").astype(str)
        .agg(" ".join, axis=1)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip().str.lower()
    )

    feat = pd.DataFrame({
        "date": df["date"],
        "is_start_semester": row_text.str.contains("개강", na=False).astype(int),
        "is_end_semester": row_text.str.contains("종강", na=False).astype(int),
        "is_exam": row_text.str.contains("시험|중간|기말", regex=True, na=False).astype(int),
        "is_vacation": row_text.str.contains("방학", na=False).astype(int),
        "is_festival": row_text.str.contains("축제", na=False).astype(int),
        "is_holiday_or_no_class": row_text.str.contains("휴강|공휴일|휴업", regex=True, na=False).astype(int),
    })

    daily = feat.groupby("date", as_index=False)[CALENDAR_FEATURE_COLS].max().sort_values("date").reset_index(drop=True)

    save = daily.copy()
    save["date"] = save["date"].dt.strftime("%Y-%m-%d")
    safe_save_csv(save, output_csv)
    print(f"Calendar features: {len(daily)} days → {output_csv.name}")
    return daily


def merge_sales_with_calendar(
    sales_csv: Path | None = None,
    calendar_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Left-join sales with calendar features on date."""
    sales_csv = sales_csv or Paths.FINAL_SALES
    calendar_csv = calendar_csv or Paths.CALENDAR_FEATURES
    output_csv = output_csv or Paths.SALES_WITH_CALENDAR

    sales = safe_read_csv(sales_csv)
    cal = safe_read_csv(calendar_csv)

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    cal["date"] = pd.to_datetime(cal["date"], errors="coerce")
    sales = sales[sales["date"].notna()].copy()
    cal = cal[cal["date"].notna()].copy()

    merged = sales.merge(cal[["date"] + CALENDAR_FEATURE_COLS], on="date", how="left")
    for c in CALENDAR_FEATURE_COLS:
        merged[c] = merged[c].fillna(0).astype(int)

    out = merged.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    safe_save_csv(out, output_csv)
    print(f"Sales+Calendar: {len(merged)} rows → {output_csv.name}")
    return merged


# ===================================================================
# Timetable features  (legacy 22, 23)
# ===================================================================

WEEKDAY_MAP = {
    "월": "monday_class_count", "화": "tuesday_class_count",
    "수": "wednesday_class_count", "목": "thursday_class_count",
    "금": "friday_class_count",
    "mon": "monday_class_count", "tue": "tuesday_class_count",
    "wed": "wednesday_class_count", "thu": "thursday_class_count",
    "fri": "friday_class_count",
}

TT_FEATURE_COLS = [
    "class_count", "monday_class_count", "tuesday_class_count",
    "wednesday_class_count", "thursday_class_count", "friday_class_count",
]


def _detect_weekday_col(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if "요일" in str(col) or "day" in str(col).lower():
            return str(col)
    best_col, best_score = None, 0
    for col in df.columns:
        s = df[col].dropna().astype(str).head(300).str.strip().str.lower()
        score = sum(1 for v in s if any(k in v for k in ["월", "화", "수", "목", "금", "mon", "tue", "wed", "thu", "fri"]))
        if score > best_score:
            best_score, best_col = score, str(col)
    return best_col if best_score > 0 else None


def _to_weekday_feature(value: str) -> str | None:
    v = str(value).strip().lower()
    for key, feat in WEEKDAY_MAP.items():
        if key in v:
            return feat
    return None


def _read_timetable_counts(file_path: Path) -> dict[str, int]:
    xls = pd.ExcelFile(file_path)
    best_df, best_col, best_score = None, None, -1
    for sheet in xls.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet)
        wc = _detect_weekday_col(df)
        if not wc:
            continue
        s = df[wc].dropna().astype(str).map(_to_weekday_feature)
        score = int(s.notna().sum())
        if score > best_score:
            best_score, best_df, best_col = score, df, wc

    if best_df is None or best_col is None:
        raise ValueError("No weekday column found in timetable file.")

    feat_cols = list(WEEKDAY_MAP.values())
    counts = {k: 0 for k in set(feat_cols)}
    for feat in best_df[best_col].dropna().astype(str).map(_to_weekday_feature).dropna():
        counts[str(feat)] += 1
    return counts


def build_timetable_features(
    sales_calendar_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Build daily timetable features (class counts per weekday)."""
    sales_calendar_csv = sales_calendar_csv or Paths.SALES_WITH_CALENDAR
    output_csv = output_csv or Paths.TIMETABLE_FEATURES

    sales = pd.read_csv(sales_calendar_csv, usecols=["date"], low_memory=False)
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales = sales[sales["date"].notna()]
    date_min, date_max = sales["date"].min(), sales["date"].max()

    counts_2425 = _read_timetable_counts(Paths.TIMETABLE_2024_2025)
    counts_2026 = _read_timetable_counts(Paths.TIMETABLE_2026)

    full_dates = pd.date_range(date_min, date_max, freq="D")
    out = pd.DataFrame({"date": full_dates})
    out["year"] = out["date"].dt.year
    out["weekday"] = out["date"].dt.weekday

    feat_cols = [
        "monday_class_count", "tuesday_class_count",
        "wednesday_class_count", "thursday_class_count", "friday_class_count",
    ]
    for c in feat_cols:
        out[c] = 0
    mask_2425 = out["year"].isin([2024, 2025])
    mask_2026 = out["year"] >= 2026
    for c in feat_cols:
        out.loc[mask_2425, c] = counts_2425.get(c, 0)
        out.loc[mask_2026, c] = counts_2026.get(c, 0)

    out["class_count"] = 0
    for i, col in enumerate(feat_cols):
        out.loc[out["weekday"] == i, "class_count"] = out[col]
    out.loc[out["weekday"].isin([5, 6]), "class_count"] = 0

    save = out.drop(columns=["year", "weekday"]).copy()
    save["date"] = save["date"].dt.strftime("%Y-%m-%d")
    safe_save_csv(save, output_csv)
    print(f"Timetable features: {len(save)} days → {output_csv.name}")
    return out


def merge_sales_with_timetable(
    sales_calendar_csv: Path | None = None,
    timetable_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Left-join sales+calendar with timetable features on date."""
    sales_calendar_csv = sales_calendar_csv or Paths.SALES_WITH_CALENDAR
    timetable_csv = timetable_csv or Paths.TIMETABLE_FEATURES
    output_csv = output_csv or Paths.SALES_WITH_CALENDAR_TIMETABLE

    sales = safe_read_csv(sales_calendar_csv)
    tt = safe_read_csv(timetable_csv)

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    tt["date"] = pd.to_datetime(tt["date"], errors="coerce")
    sales = sales[sales["date"].notna()].copy()
    tt = tt[tt["date"].notna()].copy()

    merged = sales.merge(tt[["date"] + TT_FEATURE_COLS], on="date", how="left")
    for c in TT_FEATURE_COLS:
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0)

    out = merged.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    safe_save_csv(out, output_csv)
    print(f"Sales+Timetable: {len(merged)} rows → {output_csv.name}")
    return merged


# ===================================================================
# Model features  (legacy 24)
# ===================================================================

def build_model_features(
    input_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Add lag/rolling features and target column to produce
    ``model_features.csv``.
    """
    input_csv = input_csv or Paths.SALES_WITH_CALENDAR_TIMETABLE
    output_csv = output_csv or Paths.MODEL_FEATURES
    report_path = Paths.REPORTS_DIR / "model_features_report.txt"

    df = safe_read_csv(input_csv)
    required = {"date", "plu_code", "sales_qty"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce")
    df = df[df["sales_qty"].notna()].copy()
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    df = df[(df["plu_code"] != "") & (df["plu_code"].str.lower() != "nan")].copy()

    df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)

    # Date features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    # Lag / rolling
    grp = df.groupby("plu_code", group_keys=False)
    df["sales_lag_1"] = grp["sales_qty"].shift(1)
    df["sales_lag_7"] = grp["sales_qty"].shift(7)

    shifted = grp["sales_qty"].shift(1)
    df["rolling_mean_7"] = shifted.groupby(df["plu_code"]).rolling(7).mean().reset_index(level=0, drop=True)
    df["rolling_mean_14"] = shifted.groupby(df["plu_code"]).rolling(14).mean().reset_index(level=0, drop=True)
    df["rolling_mean_28"] = shifted.groupby(df["plu_code"]).rolling(28).mean().reset_index(level=0, drop=True)

    # Target
    df["target_sales"] = grp["sales_qty"].shift(-1)

    # Drop NaN rows
    feat_cols = ["sales_lag_1", "sales_lag_7", "rolling_mean_7", "rolling_mean_14", "rolling_mean_28", "target_sales"]
    before = len(df)
    model_df = df.dropna(subset=feat_cols).copy()

    save = model_df.copy()
    save["date"] = save["date"].dt.strftime("%Y-%m-%d")
    safe_save_csv(save, output_csv)

    lines = [
        "Model Features Report",
        f"input: {input_csv.as_posix()}",
        f"initial_rows: {before}",
        f"final_rows: {len(model_df)}",
        f"date: {model_df['date'].min()} ~ {model_df['date'].max()}",
        f"plu_unique: {model_df['plu_code'].nunique()}",
    ]
    write_report(report_path, lines)
    print(f"Model features: {len(model_df)} rows → {output_csv.name}")
    return model_df
