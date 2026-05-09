from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
TIMETABLE_DIR = BASE_DIR / "data" / "raw" / "timetable"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "timetable_structure_report.txt"
TARGET_EXT = {".xlsx", ".xls", ".csv"}

TIMETABLE_KEYWORDS = ["요일", "시간", "교시", "강의명", "강의실", "수강인원"]


def normalize_text(v: object) -> str:
    return str(v).strip().replace("\n", " ")


def detect_timetable_columns(df: pd.DataFrame) -> List[str]:
    cols: List[str] = []
    for col in df.columns:
        col_text = normalize_text(col)
        if any(k in col_text for k in TIMETABLE_KEYWORDS):
            cols.append(str(col))
    return cols


def read_csv_with_fallback(file_path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(file_path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp949", low_memory=False)


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("Timetable Structure Report")
    lines.append(f"target_directory: {TIMETABLE_DIR.as_posix()}")
    lines.append("")

    if not TIMETABLE_DIR.exists():
        lines.append("ERROR: timetable directory does not exist.")
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    files = sorted([p for p in TIMETABLE_DIR.rglob("*") if p.is_file() and p.suffix.lower() in TARGET_EXT])
    lines.append(f"total_files_found: {len(files)}")
    lines.append("")

    errors: List[str] = []

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
                    timetable_cols = detect_timetable_columns(df)
                    lines.append(
                        f"    detected_timetable_columns: {timetable_cols if timetable_cols else 'None'}"
                    )
            else:
                df = read_csv_with_fallback(fp)
                lines.append("sheet_names: N/A (csv)")
                lines.append(f"columns: {list(df.columns)}")
                lines.append(f"row_count: {len(df)}")
                lines.append("top_20_rows:")
                lines.append(df.head(20).to_string(index=False))
                timetable_cols = detect_timetable_columns(df)
                lines.append(f"detected_timetable_columns: {timetable_cols if timetable_cols else 'None'}")
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
