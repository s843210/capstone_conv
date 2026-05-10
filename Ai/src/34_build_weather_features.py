from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
WEATHER_DIR = BASE_DIR / "data" / "raw" / "weather"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "weather_features.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "weather_features_report.txt"

STANDARD_COLUMNS = ["date", "avg_temp", "min_temp", "max_temp", "rainfall"]

COLUMN_ALIASES: Dict[str, List[str]] = {
    "date": ["일시", "date"],
    "avg_temp": ["평균기온(°C)", "평균기온", "avg_temp"],
    "min_temp": ["최저기온(°C)", "최저기온", "min_temp"],
    "max_temp": ["최고기온(°C)", "최고기온", "max_temp"],
    "rainfall": ["일강수량(mm)", "일강수량", "rainfall"],
}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_col_key(text: object) -> str:
    val = str(text).strip().lower()
    for ch in [" ", "_", "-", "/", "(", ")", "[", "]", "."]:
        val = val.replace(ch, "")
    return val


def read_csv_with_fallback(path: Path) -> tuple[pd.DataFrame, str]:
    try:
        return pd.read_csv(path, encoding="utf-8", low_memory=False), "utf-8"
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", low_memory=False), "cp949"


def build_rename_map(columns: List[str]) -> Dict[str, str]:
    rename_map: Dict[str, str] = {}
    normalized = {normalize_col_key(c): c for c in columns}

    for standard, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = normalize_col_key(alias)
            if key in normalized:
                rename_map[normalized[key]] = standard
                break

    return rename_map


def load_and_standardize_one_csv(path: Path) -> tuple[pd.DataFrame, str]:
    raw, encoding_used = read_csv_with_fallback(path)
    rename_map = build_rename_map([str(c) for c in raw.columns])
    df = raw.rename(columns=rename_map)

    missing = [c for c in STANDARD_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"required columns not found: {missing}")

    out = df[STANDARD_COLUMNS].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")

    for col in ["avg_temp", "min_temp", "max_temp", "rainfall"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["rainfall"] = out["rainfall"].fillna(0)
    out = out.dropna(subset=["date"]).copy()

    return out, encoding_used


def build_report(df: pd.DataFrame, file_count: int, encodings: List[str]) -> str:
    lines: List[str] = []
    lines.append("Weather Features Report")
    lines.append(f"source_directory: {WEATHER_DIR.as_posix()}")
    lines.append(f"source_csv_files: {file_count}")
    lines.append(f"encodings_used: {encodings}")
    lines.append("")

    lines.append(f"row_count: {len(df)}")
    if len(df) > 0:
        lines.append(f"date_min: {df['date'].min().date()}")
        lines.append(f"date_max: {df['date'].max().date()}")
    else:
        lines.append("date_min: None")
        lines.append("date_max: None")

    lines.append("")
    lines.append("missing_by_column:")
    missing = df.isna().sum()
    for col in STANDARD_COLUMNS:
        lines.append(f"- {col}: {int(missing.get(col, 0))}")

    lines.append("")
    lines.append("numeric_statistics:")
    stat_cols = ["avg_temp", "min_temp", "max_temp", "rainfall"]
    if len(df) == 0:
        lines.append("(empty dataframe)")
    else:
        stats = df[stat_cols].describe().transpose()
        lines.append(stats.to_string())

    return "\n".join(lines)


def main() -> None:
    ensure_parent(OUTPUT_CSV)
    ensure_parent(REPORT_PATH)

    if not WEATHER_DIR.exists():
        raise FileNotFoundError(f"weather directory does not exist: {WEATHER_DIR}")

    csv_files = sorted(
        p for p in WEATHER_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() == ".csv"
    )
    if not csv_files:
        raise FileNotFoundError("No CSV files found under data/raw/weather")

    frames: List[pd.DataFrame] = []
    encodings: List[str] = []

    for fp in csv_files:
        df, enc = load_and_standardize_one_csv(fp)
        frames.append(df)
        encodings.append(enc)

    merged = pd.concat(frames, ignore_index=True)

    weather_features = (
        merged.groupby("date", as_index=False)
        .agg(
            avg_temp=("avg_temp", "mean"),
            min_temp=("min_temp", "mean"),
            max_temp=("max_temp", "mean"),
            rainfall=("rainfall", "sum"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )

    weather_features = weather_features[STANDARD_COLUMNS].copy()
    weather_features["date"] = weather_features["date"].dt.strftime("%Y-%m-%d")

    weather_features.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    report_text = build_report(
        pd.read_csv(OUTPUT_CSV, parse_dates=["date"]),
        file_count=len(csv_files),
        encodings=encodings,
    )
    REPORT_PATH.write_text(report_text, encoding="utf-8")

    print(f"Saved weather features: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Rows: {len(weather_features)}")


if __name__ == "__main__":
    main()
