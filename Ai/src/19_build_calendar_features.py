from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "raw" / "calendar" / "academic_calendar_2026.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "academic_calendar_features.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "academic_calendar_features_report.txt"


def parse_date_series(series: pd.Series) -> pd.Series:
    # Supports values like 260303 (YYMMDD) and normal date strings.
    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, format="%y%m%d", errors="coerce")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        fallback = pd.to_datetime(s, errors="coerce")
    return parsed.fillna(fallback)


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    try:
        df = pd.read_csv(INPUT_CSV, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(INPUT_CSV, encoding="cp949", low_memory=False)

    if "date" not in df.columns:
        raise KeyError("'date' column not found in calendar file.")

    # 2) date conversion
    df["date"] = parse_date_series(df["date"])
    df = df[df["date"].notna()].copy()

    # 3) detect text columns likely holding event content
    text_cols = []
    for col in df.columns:
        if col == "date":
            continue
        if df[col].dtype == "object" or str(df[col].dtype).startswith("string"):
            text_cols.append(col)
            continue
        col_name = str(col).lower()
        if any(k in col_name for k in ["event", "내용", "일정", "행사", "비고"]):
            text_cols.append(col)

    if not text_cols:
        # fallback: use all non-date columns as text
        text_cols = [c for c in df.columns if c != "date"]

    # Build merged text per row
    row_text = (
        df[text_cols]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.lower()
    )

    # 4) feature flags
    feat = pd.DataFrame(
        {
            "date": df["date"],
            "is_start_semester": row_text.str.contains("개강", na=False).astype(int),
            "is_end_semester": row_text.str.contains("종강", na=False).astype(int),
            "is_exam": row_text.str.contains("시험|중간|기말", regex=True, na=False).astype(int),
            "is_vacation": row_text.str.contains("방학", na=False).astype(int),
            "is_festival": row_text.str.contains("축제", na=False).astype(int),
            "is_holiday_or_no_class": row_text.str.contains("휴강|공휴일|휴업", regex=True, na=False).astype(int),
        }
    )

    # 5) group by date with OR logic via max
    agg_cols = [c for c in feat.columns if c != "date"]
    daily_feat = feat.groupby("date", as_index=False)[agg_cols].max().sort_values("date").reset_index(drop=True)

    # save
    save_df = daily_feat.copy()
    save_df["date"] = save_df["date"].dt.strftime("%Y-%m-%d")
    save_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    lines: list[str] = []
    lines.append("Academic Calendar Features Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"input_rows: {len(df)}")
    lines.append(f"output_daily_rows: {len(daily_feat)}")
    lines.append(f"date_min: {daily_feat['date'].min()}")
    lines.append(f"date_max: {daily_feat['date'].max()}")
    lines.append(f"detected_text_columns: {text_cols}")
    lines.append("")
    lines.append("[Feature Sums]")
    for col in agg_cols:
        lines.append(f"{col}: {int(daily_feat[col].sum())}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved features: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Output rows: {len(daily_feat)}")


if __name__ == "__main__":
    main()
