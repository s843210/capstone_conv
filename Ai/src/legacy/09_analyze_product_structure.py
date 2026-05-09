from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PRODUCT_DIR = BASE_DIR / "data" / "raw" / "product"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "product_structure_report.txt"
TARGET_EXTENSIONS = {".xlsx", ".xls", ".csv"}


@dataclass
class FileError:
    path: Path
    error: str


def format_top_rows(df: pd.DataFrame, n: int = 5) -> str:
    if df.empty:
        return "(empty dataframe)"
    return df.head(n).to_string(index=False)


def analyze_excel(file_path: Path, errors: List[FileError]) -> List[str]:
    lines: List[str] = []
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as exc:
        errors.append(FileError(file_path, f"Failed to open excel file: {exc}"))
        return lines

    lines.append(f"sheet_names: {xls.sheet_names}")
    for sheet_name in xls.sheet_names:
        lines.append(f"  - sheet: {sheet_name}")
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            lines.append(f"    columns: {list(df.columns)}")
            lines.append(f"    row_count: {len(df)}")
            lines.append("    top_5_rows:")
            for row_line in format_top_rows(df, 5).splitlines():
                lines.append(f"      {row_line}")
        except Exception as exc:
            errors.append(FileError(file_path, f"Failed to read sheet '{sheet_name}': {exc}"))
            lines.append("    columns: N/A")
            lines.append("    row_count: N/A")
            lines.append("    top_5_rows:")
            lines.append("      (failed to read this sheet)")
    return lines


def analyze_csv(file_path: Path, errors: List[FileError]) -> List[str]:
    lines: List[str] = ["sheet_names: N/A (not an excel file)"]
    try:
        df = pd.read_csv(file_path, low_memory=False)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_path, low_memory=False, encoding="cp949")
        except Exception as exc:
            errors.append(FileError(file_path, f"Failed to read csv file: {exc}"))
            lines.append("columns: N/A")
            lines.append("row_count: N/A")
            lines.append("top_5_rows:")
            lines.append("  (failed to read this file)")
            return lines
    except Exception as exc:
        errors.append(FileError(file_path, f"Failed to read csv file: {exc}"))
        lines.append("columns: N/A")
        lines.append("row_count: N/A")
        lines.append("top_5_rows:")
        lines.append("  (failed to read this file)")
        return lines

    lines.append(f"columns: {list(df.columns)}")
    lines.append(f"row_count: {len(df)}")
    lines.append("top_5_rows:")
    for row_line in format_top_rows(df, 5).splitlines():
        lines.append(f"  {row_line}")
    return lines


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    errors: List[FileError] = []
    report_lines: List[str] = []

    report_lines.append("Product Master Structure Report")
    report_lines.append(f"target_directory: {PRODUCT_DIR.as_posix()}")
    report_lines.append("")

    if not PRODUCT_DIR.exists():
        report_lines.append("ERROR: product directory does not exist.")
        REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    files = sorted(
        [p for p in PRODUCT_DIR.rglob("*") if p.is_file() and p.suffix.lower() in TARGET_EXTENSIONS]
    )
    report_lines.append(f"total_files_found: {len(files)}")
    report_lines.append("")

    for file_path in files:
        rel = file_path.relative_to(BASE_DIR).as_posix()
        report_lines.append("=" * 100)
        report_lines.append(f"file_name: {file_path.name}")
        report_lines.append(f"extension: {file_path.suffix.lower()}")
        report_lines.append(f"path: {rel}")

        ext = file_path.suffix.lower()
        if ext in {".xlsx", ".xls"}:
            report_lines.extend(analyze_excel(file_path, errors))
        elif ext == ".csv":
            report_lines.extend(analyze_csv(file_path, errors))
        report_lines.append("")

    report_lines.append("#" * 100)
    report_lines.append("ERROR LOG")
    if errors:
        for e in errors:
            report_lines.append(f"- path: {e.path.relative_to(BASE_DIR).as_posix()}")
            report_lines.append(f"  error: {e.error}")
    else:
        report_lines.append("No errors.")

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report saved: {REPORT_PATH}")
    print(f"Total files analyzed: {len(files)}")
    print(f"Total errors logged: {len(errors)}")


if __name__ == "__main__":
    main()
