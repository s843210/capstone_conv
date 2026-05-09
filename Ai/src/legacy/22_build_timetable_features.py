from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
TT_2024_2025 = BASE_DIR / "data" / "raw" / "timetable" / "timetable_2024_2025.xlsx"
TT_2026 = BASE_DIR / "data" / "raw" / "timetable" / "timetable_2026.xlsx"
SALES_CALENDAR_CSV = BASE_DIR / "data" / "processed" / "sales_with_calendar.csv"

OUTPUT_CSV = BASE_DIR / "data" / "processed" / "timetable_features.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "timetable_features_report.txt"

WEEKDAY_MAP = {
    "월": "monday_class_count",
    "화": "tuesday_class_count",
    "수": "wednesday_class_count",
    "목": "thursday_class_count",
    "금": "friday_class_count",
    "mon": "monday_class_count",
    "tue": "tuesday_class_count",
    "wed": "wednesday_class_count",
    "thu": "thursday_class_count",
    "fri": "friday_class_count",
}


def normalize(v: object) -> str:
    return str(v).strip().lower()


def detect_weekday_column(df: pd.DataFrame) -> str | None:
    # 1) header keyword priority
    for col in df.columns:
        c = str(col)
        if "요일" in c or "day" in c.lower():
            return str(col)

    # 2) value-pattern based score
    best_col = None
    best_score = 0
    for col in df.columns:
        s = df[col].dropna().astype(str).head(300).map(normalize)
        if s.empty:
            continue
        score = 0
        for v in s:
            if any(k in v for k in ["월", "화", "수", "목", "금", "mon", "tue", "wed", "thu", "fri"]):
                score += 1
        if score > best_score:
            best_score = score
            best_col = str(col)
    return best_col if best_score > 0 else None


def detect_time_or_period_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        c = str(col)
        if any(k in c for k in ["시간", "교시", "period", "time"]):
            return str(col)
    return None


def to_weekday_feature(value: str) -> str | None:
    v = normalize(value)
    # Prefer English tokens first
    for key, feat in WEEKDAY_MAP.items():
        if key in v:
            return feat
    return None


def read_timetable_and_count(file_path: Path) -> tuple[dict[str, int], str, str, int]:
    if not file_path.exists():
        raise FileNotFoundError(f"Timetable file not found: {file_path}")

    xls = pd.ExcelFile(file_path)
    best_sheet = None
    best_df = None
    best_weekday_col = None
    best_score = -1

    # choose sheet with most weekday-like rows
    for sheet in xls.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet)
        weekday_col = detect_weekday_column(df)
        if not weekday_col:
            continue
        s = df[weekday_col].dropna().astype(str).map(to_weekday_feature)
        score = int(s.notna().sum())
        if score > best_score:
            best_score = score
            best_sheet = sheet
            best_df = df
            best_weekday_col = weekday_col

    if best_df is None or best_weekday_col is None or best_sheet is None:
        raise ValueError("Could not detect usable weekday column in any sheet.")

    time_col = detect_time_or_period_column(best_df)

    feat_cols = [
        "monday_class_count",
        "tuesday_class_count",
        "wednesday_class_count",
        "thursday_class_count",
        "friday_class_count",
    ]
    counts = {k: 0 for k in feat_cols}

    weekday_features = best_df[best_weekday_col].dropna().astype(str).map(to_weekday_feature)
    for feat in weekday_features.dropna():
        counts[str(feat)] += 1

    return counts, best_sheet, best_weekday_col, 0 if time_col is None else 1


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_CALENDAR_CSV.exists():
        raise FileNotFoundError(f"Sales+calendar file not found: {SALES_CALENDAR_CSV}")

    sales = pd.read_csv(SALES_CALENDAR_CSV, usecols=["date"], low_memory=False)
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales = sales[sales["date"].notna()]
    if sales.empty:
        raise ValueError("No valid dates in sales_with_calendar.csv")

    date_min = sales["date"].min()
    date_max = sales["date"].max()

    counts_2425, sheet_2425, weekday_col_2425, has_time_2425 = read_timetable_and_count(TT_2024_2025)
    counts_2026, sheet_2026, weekday_col_2026, has_time_2026 = read_timetable_and_count(TT_2026)

    full_dates = pd.date_range(date_min, date_max, freq="D")
    out = pd.DataFrame({"date": full_dates})
    out["year"] = out["date"].dt.year
    out["weekday"] = out["date"].dt.weekday  # Mon=0 ... Sun=6

    feat_cols = [
        "monday_class_count",
        "tuesday_class_count",
        "wednesday_class_count",
        "thursday_class_count",
        "friday_class_count",
    ]
    for c in feat_cols:
        out[c] = 0

    # 2024~2025 counts for 2024/2025, 2026 counts for 2026+
    mask_2425 = out["year"].isin([2024, 2025])
    mask_2026 = out["year"] >= 2026
    for c in feat_cols:
        out.loc[mask_2425, c] = counts_2425[c]
        out.loc[mask_2026, c] = counts_2026[c]

    # 6) assign class_count by weekday, 7) weekend 0
    out["class_count"] = 0
    out.loc[out["weekday"] == 0, "class_count"] = out["monday_class_count"]
    out.loc[out["weekday"] == 1, "class_count"] = out["tuesday_class_count"]
    out.loc[out["weekday"] == 2, "class_count"] = out["wednesday_class_count"]
    out.loc[out["weekday"] == 3, "class_count"] = out["thursday_class_count"]
    out.loc[out["weekday"] == 4, "class_count"] = out["friday_class_count"]
    out.loc[out["weekday"].isin([5, 6]), "class_count"] = 0

    save_df = out.drop(columns=["year", "weekday"]).copy()
    save_df["date"] = save_df["date"].dt.strftime("%Y-%m-%d")
    save_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 9~10) report
    lines: list[str] = []
    lines.append("Timetable Features Report")
    lines.append(f"sales_reference: {SALES_CALENDAR_CSV.as_posix()}")
    lines.append(f"timetable_2024_2025: {TT_2024_2025.as_posix()}")
    lines.append(f"timetable_2026: {TT_2026.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"date_min: {date_min}")
    lines.append(f"date_max: {date_max}")
    lines.append(f"output_rows: {len(save_df)}")
    lines.append("")
    lines.append("[Detected Columns]")
    lines.append(f"2024_2025_sheet: {sheet_2425}")
    lines.append(f"2024_2025_weekday_col: {weekday_col_2425}")
    lines.append(f"2024_2025_has_time_or_period_col: {has_time_2425}")
    lines.append(f"2026_sheet: {sheet_2026}")
    lines.append(f"2026_weekday_col: {weekday_col_2026}")
    lines.append(f"2026_has_time_or_period_col: {has_time_2026}")
    lines.append("")
    lines.append("[Weekday Counts Used]")
    lines.append(f"2024_2025_counts: {counts_2425}")
    lines.append(f"2026_counts: {counts_2026}")
    lines.append("")
    lines.append("[class_count Stats]")
    lines.append(f"class_count_min: {int(save_df['class_count'].min())}")
    lines.append(f"class_count_max: {int(save_df['class_count'].max())}")
    lines.append(f"class_count_mean: {float(save_df['class_count'].mean())}")
    lines.append(f"weekend_zero_days: {int((out['weekday'].isin([5, 6]) & (save_df['class_count'] == 0)).sum())}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved features: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Output rows: {len(save_df)}")


if __name__ == "__main__":
    main()
