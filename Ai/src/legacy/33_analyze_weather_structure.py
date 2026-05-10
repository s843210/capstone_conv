from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import re


BASE_DIR = Path(__file__).resolve().parents[1]
WEATHER_DIR = BASE_DIR / "data" / "raw" / "weather"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "weather_structure_report.txt"
TARGET_EXT = {".csv", ".xlsx", ".xls"}

DATE_KEYWORDS = [
    "date",
    "day",
    "일자",
    "날짜",
    "년월일",
    "관측일",
    "기준일",
]

WEATHER_COLUMN_KEYWORDS: Dict[str, List[str]] = {
    "avg_temp": ["평균기온", "평균 기온", "avgtemp", "avg_temp", "tavg", "mean_temp"],
    "max_temp": ["최고기온", "최고 기온", "maxtemp", "max_temp", "tmax", "high_temp"],
    "min_temp": ["최저기온", "최저 기온", "mintemp", "min_temp", "tmin", "low_temp"],
    "precipitation": ["일강수량", "강수량", "강수", "precip", "rainfall", "prcp"],
}


def normalize_text(value: object) -> str:
    return str(value).strip().replace("\n", " ")


def normalize_key(value: object) -> str:
    text = normalize_text(value).lower()
    for ch in [" ", "_", "-", "/", "(", ")", "[", "]", "."]:
        text = text.replace(ch, "")
    return text


def read_csv_with_fallback(file_path: Path) -> tuple[pd.DataFrame, str]:
    try:
        return pd.read_csv(file_path, encoding="utf-8", low_memory=False), "utf-8"
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp949", low_memory=False), "cp949"


def detect_date_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        col_text = normalize_text(col)
        key = normalize_key(col)
        if any(k in col_text for k in DATE_KEYWORDS) or any(k in key for k in DATE_KEYWORDS):
            return str(col)

    # Fallback 1: infer date column by explicit date-pattern match.
    date_pattern = re.compile(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$")
    for col in df.columns:
        sample = df[col].dropna().astype(str).str.strip().head(100)
        if sample.empty:
            continue
        ratio = sample.str.match(date_pattern).mean()
        if ratio >= 0.8:
            return str(col)

    # Fallback 2: infer date column by parse success rate from sample values.
    for col in df.columns:
        sample = df[col].dropna().astype(str).str.strip().head(100)
        if sample.empty:
            continue
        separator_ratio = sample.str.contains(r"[-/.]").mean()
        if separator_ratio < 0.5:
            continue
        parsed = pd.to_datetime(sample, errors="coerce")
        success_ratio = parsed.notna().mean()
        if success_ratio >= 0.8:
            return str(col)

    return None


def detect_weather_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    found: Dict[str, Optional[str]] = {
        "avg_temp": None,
        "max_temp": None,
        "min_temp": None,
        "precipitation": None,
    }

    for col in df.columns:
        col_text = normalize_text(col)
        key = normalize_key(col)
        for weather_type, keywords in WEATHER_COLUMN_KEYWORDS.items():
            if found[weather_type] is not None:
                continue
            for kw in keywords:
                kw_key = normalize_key(kw)
                if kw in col_text or kw_key in key:
                    found[weather_type] = str(col)
                    break

    return found


def append_df_analysis(lines: List[str], df: pd.DataFrame, section_prefix: str = "") -> None:
    date_col = detect_date_column(df)
    weather_cols = detect_weather_columns(df)

    lines.append(f"{section_prefix}columns: {list(df.columns)}")
    lines.append(f"{section_prefix}row_count: {len(df)}")
    lines.append(f"{section_prefix}detected_date_column: {date_col if date_col else 'None'}")
    lines.append(f"{section_prefix}detected_avg_temp_column: {weather_cols['avg_temp'] if weather_cols['avg_temp'] else 'None'}")
    lines.append(f"{section_prefix}detected_max_temp_column: {weather_cols['max_temp'] if weather_cols['max_temp'] else 'None'}")
    lines.append(f"{section_prefix}detected_min_temp_column: {weather_cols['min_temp'] if weather_cols['min_temp'] else 'None'}")
    lines.append(
        f"{section_prefix}detected_precipitation_column: "
        f"{weather_cols['precipitation'] if weather_cols['precipitation'] else 'None'}"
    )
    lines.append(f"{section_prefix}top_20_rows:")
    if df.empty:
        lines.append(f"{section_prefix}(empty dataframe)")
    else:
        lines.append(df.head(20).to_string(index=False))


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("Weather Structure Report")
    lines.append(f"target_directory: {WEATHER_DIR.as_posix()}")
    lines.append("")

    if not WEATHER_DIR.exists():
        lines.append("ERROR: weather directory does not exist.")
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    files = sorted(
        p for p in WEATHER_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in TARGET_EXT
    )

    lines.append(f"total_files_found: {len(files)}")
    lines.append("")

    errors: List[str] = []

    for fp in files:
        rel_path = fp.relative_to(BASE_DIR).as_posix()
        lines.append("=" * 100)
        lines.append(f"file_name: {fp.name}")
        lines.append(f"extension: {fp.suffix.lower()}")
        lines.append(f"path: {rel_path}")

        try:
            ext = fp.suffix.lower()
            if ext == ".csv":
                df, used_encoding = read_csv_with_fallback(fp)
                lines.append(f"encoding_used: {used_encoding}")
                append_df_analysis(lines, df)
            else:
                xls = pd.ExcelFile(fp)
                lines.append("encoding_used: N/A (excel)")
                lines.append(f"sheet_names: {xls.sheet_names}")
                for sheet_name in xls.sheet_names:
                    lines.append(f"sheet: {sheet_name}")
                    df = pd.read_excel(fp, sheet_name=sheet_name)
                    append_df_analysis(lines, df, section_prefix="  ")
                    lines.append("")
        except Exception as exc:
            errors.append(f"{rel_path} -> {exc}")
            lines.append(f"ERROR: failed to analyze file: {exc}")

        lines.append("")

    lines.append("#" * 100)
    lines.append("ERROR LOG")
    if errors:
        lines.extend(errors)
    else:
        lines.append("No errors.")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report saved: {REPORT_PATH}")
    print(f"Total files analyzed: {len(files)}")
    print(f"Total errors: {len(errors)}")


if __name__ == "__main__":
    main()
