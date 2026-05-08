from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_DIR = BASE_DIR / "data" / "raw" / "sales"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "sales_structure_report.txt"


@dataclass
class FileError:
    path: Path
    error: str


def format_top_rows(df: pd.DataFrame, n: int = 3) -> str:
    if df.empty:
        return "(empty dataframe)"
    return df.head(n).to_string(index=False)


def analyze_excel(file_path: Path, errors: List[FileError]) -> List[str]:
    lines: List[str] = []
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as exc:  # pragma: no cover
        errors.append(FileError(file_path, f"Failed to open excel file: {exc}"))
        return lines

    sheet_names = xls.sheet_names
    lines.append(f"sheet_names: {sheet_names}")
    for sheet_name in sheet_names:
        lines.append(f"  - sheet: {sheet_name}")
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            lines.append(f"    columns: {list(df.columns)}")
            lines.append(f"    row_count: {len(df)}")
            lines.append("    top_3_rows:")
            top_rows = format_top_rows(df, 3)
            for row_line in top_rows.splitlines():
                lines.append(f"      {row_line}")
        except Exception as exc:  # pragma: no cover
            errors.append(
                FileError(file_path, f"Failed to read sheet '{sheet_name}': {exc}")
            )
            lines.append("    columns: N/A")
            lines.append("    row_count: N/A")
            lines.append("    top_3_rows:")
            lines.append("      (failed to read this sheet)")
    return lines


def analyze_delimited(file_path: Path, errors: List[FileError]) -> List[str]:
    lines: List[str] = []
    ext = file_path.suffix.lower()
    sep = ","
    if ext == ".tsv":
        sep = "\t"

    lines.append("sheet_names: N/A (not an excel file)")
    try:
        # Keep low_memory=False for consistent dtype inference across chunks.
        df = pd.read_csv(file_path, sep=sep, low_memory=False)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_path, sep=sep, low_memory=False, encoding="cp949")
        except Exception as exc:  # pragma: no cover
            errors.append(FileError(file_path, f"Failed to read delimited file: {exc}"))
            lines.append("columns: N/A")
            lines.append("row_count: N/A")
            lines.append("top_3_rows:")
            lines.append("  (failed to read this file)")
            return lines
    except Exception as exc:  # pragma: no cover
        errors.append(FileError(file_path, f"Failed to read delimited file: {exc}"))
        lines.append("columns: N/A")
        lines.append("row_count: N/A")
        lines.append("top_3_rows:")
        lines.append("  (failed to read this file)")
        return lines

    lines.append(f"columns: {list(df.columns)}")
    lines.append(f"row_count: {len(df)}")
    lines.append("top_3_rows:")
    top_rows = format_top_rows(df, 3)
    for row_line in top_rows.splitlines():
        lines.append(f"  {row_line}")
    return lines


def analyze_file(file_path: Path, errors: List[FileError]) -> List[str]:
    lines: List[str] = []
    relative_path = file_path.relative_to(BASE_DIR)

    lines.append("=" * 100)
    lines.append(f"file_name: {file_path.name}")
    lines.append(f"extension: {file_path.suffix.lower()}")
    lines.append(f"path: {relative_path.as_posix()}")

    ext = file_path.suffix.lower()
    if ext in {".xlsx", ".xls", ".xlsm"}:
        lines.extend(analyze_excel(file_path, errors))
    elif ext in {".csv", ".tsv", ".txt"}:
        lines.extend(analyze_delimited(file_path, errors))
    else:
        errors.append(FileError(file_path, f"Unsupported extension: {ext}"))
        lines.append("sheet_names: N/A")
        lines.append("columns: N/A")
        lines.append("row_count: N/A")
        lines.append("top_3_rows:")
        lines.append("  (unsupported file type)")

    return lines


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    errors: List[FileError] = []

    report_lines: List[str] = []
    report_lines.append("Sales Data Structure Report")
    report_lines.append(f"target_directory: {SALES_DIR.as_posix()}")
    report_lines.append("")

    if not SALES_DIR.exists():
        report_lines.append("ERROR: sales directory does not exist.")
        REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    all_files = sorted([p for p in SALES_DIR.rglob("*") if p.is_file()])
    report_lines.append(f"total_files_found: {len(all_files)}")
    report_lines.append("")

    for file_path in all_files:
        report_lines.extend(analyze_file(file_path, errors))
        report_lines.append("")

    report_lines.append("#" * 100)
    report_lines.append("ERROR LOG")
    if errors:
        for err in errors:
            rel = err.path.relative_to(BASE_DIR).as_posix()
            report_lines.append(f"- path: {rel}")
            report_lines.append(f"  error: {err.error}")
    else:
        report_lines.append("No errors.")

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report saved: {REPORT_PATH}")
    print(f"Total files analyzed: {len(all_files)}")
    print(f"Total errors logged: {len(errors)}")


if __name__ == "__main__":
    main()
