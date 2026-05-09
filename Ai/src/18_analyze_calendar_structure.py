from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Iterable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
CALENDAR_DIR = BASE_DIR / "data" / "raw" / "calendar"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "calendar_structure_report.txt"
TARGET_EXT = {".xlsx", ".xls", ".csv"}

EVENT_KEYWORDS = ["개강", "종강", "시험", "축제", "방학", "휴강"]


def normalize_text(v: object) -> str:
    s = str(v).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def detect_date_columns(df: pd.DataFrame) -> list[str]:
    date_cols: list[str] = []
    for col in df.columns:
        col_str = normalize_text(col)
        if any(k in col_str for k in ["일자", "날짜", "date", "Date", "DATE"]):
            date_cols.append(str(col))
            continue

        sample = df[col].dropna().head(50)
        if sample.empty:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(sample, errors="coerce")
        valid_ratio = float(parsed.notna().mean())
        if valid_ratio >= 0.6:
            date_cols.append(str(col))
    return date_cols


def find_event_hits(df: pd.DataFrame, keywords: Iterable[str], max_hits: int = 30) -> list[str]:
    hits: list[str] = []
    for _, row in df.head(500).iterrows():
        row_text = " | ".join([normalize_text(v) for v in row.tolist()])
        if not row_text:
            continue
        for kw in keywords:
            if kw in row_text:
                hits.append(f"[{kw}] {row_text}")
                break
        if len(hits) >= max_hits:
            break
    return hits


def read_csv_with_fallback(file_path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(file_path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp949", low_memory=False)


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("Calendar Structure Report")
    lines.append(f"target_directory: {CALENDAR_DIR.as_posix()}")
    lines.append("")

    if not CALENDAR_DIR.exists():
        lines.append("ERROR: calendar directory does not exist.")
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    files = sorted([p for p in CALENDAR_DIR.rglob("*") if p.is_file() and p.suffix.lower() in TARGET_EXT])
    lines.append(f"total_files_found: {len(files)}")
    lines.append("")

    errors: list[str] = []

    for fp in files:
        rel = fp.relative_to(BASE_DIR).as_posix()
        lines.append("=" * 100)
        lines.append(f"file_name: {fp.name}")
        lines.append(f"extension: {fp.suffix.lower()}")
        lines.append(f"path: {rel}")

        try:
            if fp.suffix.lower() in {".xlsx", ".xls"}:
                xls = pd.ExcelFile(fp)
                lines.append(f"sheet_names: {xls.sheet_names}")
                for sheet in xls.sheet_names:
                    lines.append(f"  - sheet: {sheet}")
                    df = pd.read_excel(fp, sheet_name=sheet)
                    lines.append(f"    columns: {list(df.columns)}")
                    lines.append(f"    row_count: {len(df)}")
                    lines.append("    top_20_rows:")
                    lines.append(df.head(20).to_string(index=False))

                    date_cols = detect_date_columns(df)
                    lines.append(f"    detected_date_columns: {date_cols if date_cols else 'None'}")

                    hits = find_event_hits(df, EVENT_KEYWORDS, max_hits=20)
                    lines.append("    event_keyword_hits:")
                    if hits:
                        for h in hits:
                            lines.append(f"      {h}")
                    else:
                        lines.append("      None")
            else:
                df = read_csv_with_fallback(fp)
                lines.append("sheet_names: N/A (csv)")
                lines.append(f"columns: {list(df.columns)}")
                lines.append(f"row_count: {len(df)}")
                lines.append("top_20_rows:")
                lines.append(df.head(20).to_string(index=False))

                date_cols = detect_date_columns(df)
                lines.append(f"detected_date_columns: {date_cols if date_cols else 'None'}")

                hits = find_event_hits(df, EVENT_KEYWORDS, max_hits=20)
                lines.append("event_keyword_hits:")
                if hits:
                    for h in hits:
                        lines.append(f"  {h}")
                else:
                    lines.append("  None")
        except Exception as exc:
            errors.append(f"{rel} -> {exc}")
            lines.append(f"ERROR: failed to read file: {exc}")

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
