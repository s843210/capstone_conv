from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
WEATHER_DIR = BASE_DIR / "data" / "raw" / "weather"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "weather_features.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "weather_features_v2_report.txt"
TARGET_EXT = {".csv", ".xlsx", ".xls"}

STANDARD_COLUMNS = ["date", "avg_temp", "min_temp", "max_temp", "rainfall"]
COLUMN_ALIASES: Dict[str, List[str]] = {
    "date": ["일시", "date"],
    "avg_temp": ["평균기온(°C)", "평균기온", "avg_temp"],
    "min_temp": ["최저기온(°C)", "최저기온", "min_temp"],
    "max_temp": ["최고기온(°C)", "최고기온", "max_temp"],
    "rainfall": ["일강수량(mm)", "일강수량", "rainfall"],
}


def normalize_col_key(text: object) -> str:
    val = str(text).strip().lower()
    for ch in [" ", "_", "-", "/", "(", ")", "[", "]", "."]:
        val = val.replace(ch, "")
    return val


def build_rename_map(columns: List[str]) -> Dict[str, str]:
    rename_map: Dict[str, str] = {}
    normalized = {normalize_col_key(c): c for c in columns}
    for std, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = normalize_col_key(alias)
            if key in normalized:
                rename_map[normalized[key]] = std
                break
    return rename_map


def read_csv_with_fallback(path: Path) -> Tuple[pd.DataFrame, str]:
    try:
        return pd.read_csv(path, encoding="utf-8", low_memory=False), "utf-8"
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", low_memory=False), "cp949"


def load_one_file(path: Path) -> Tuple[pd.DataFrame, str]:
    ext = path.suffix.lower()
    if ext == ".csv":
        raw, enc = read_csv_with_fallback(path)
    else:
        raw = pd.read_excel(path)
        enc = "N/A(excel)"

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
    return out, enc


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not WEATHER_DIR.exists():
        raise FileNotFoundError(f"weather directory does not exist: {WEATHER_DIR}")

    files = sorted(p for p in WEATHER_DIR.rglob("*") if p.is_file() and p.suffix.lower() in TARGET_EXT)
    if not files:
        raise FileNotFoundError("No weather files (.csv/.xlsx/.xls) found under data/raw/weather")

    frames: List[pd.DataFrame] = []
    file_logs: List[str] = []
    success = 0
    failed = 0

    for fp in files:
        rel = fp.relative_to(BASE_DIR).as_posix()
        try:
            one, enc = load_one_file(fp)
            frames.append(one)
            file_logs.append(f"- SUCCESS | {rel} | encoding={enc} | rows={len(one)}")
            success += 1
        except Exception as exc:
            file_logs.append(f"- FAILED | {rel} | {exc}")
            failed += 1

    if not frames:
        raise RuntimeError("All weather files failed to parse.")

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
    weather_features["rainfall"] = weather_features["rainfall"].fillna(0)
    weather_features = weather_features[STANDARD_COLUMNS].copy()
    weather_features["date"] = weather_features["date"].dt.strftime("%Y-%m-%d")
    weather_features.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    check_df = pd.read_csv(OUTPUT_CSV, parse_dates=["date"])
    lines: List[str] = []
    lines.append("Weather Features V2 Report")
    lines.append(f"source_directory: {WEATHER_DIR.as_posix()}")
    lines.append(f"processed_files: {len(files)}")
    lines.append(f"success_files: {success}")
    lines.append(f"failed_files: {failed}")
    lines.append(f"row_count: {len(check_df)}")
    lines.append(f"date_min: {check_df['date'].min()}")
    lines.append(f"date_max: {check_df['date'].max()}")
    lines.append("")
    lines.append("missing_by_column:")
    miss = check_df.isna().sum()
    for col in STANDARD_COLUMNS:
        lines.append(f"- {col}: {int(miss.get(col, 0))}")
    lines.append("")
    lines.append("[file_results]")
    lines.extend(file_logs)

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved weather features: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Processed files: {len(files)} (success={success}, failed={failed})")
    print(f"Rows: {len(check_df)}")


if __name__ == "__main__":
    main()
