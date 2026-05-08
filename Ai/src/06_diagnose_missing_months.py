from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_DIR = BASE_DIR / "data" / "raw" / "sales"
MERGED_CSV = BASE_DIR / "data" / "processed" / "daily_sales_raw.csv"
MERGE_LOG = BASE_DIR / "outputs" / "reports" / "merge_sales_log.txt"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "missing_months_diagnosis.txt"
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}


def month_from_sales_dir_name(name: str) -> str | None:
    m = re.fullmatch(r"sales_(\d{4})_(\d{2})", name)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def parse_failed_files_from_log(log_text: str) -> set[str]:
    failed = set()
    for line in log_text.splitlines():
        line = line.strip()
        if line.startswith("- file: "):
            failed.add(line.replace("- file: ", "", 1).strip())
    return failed


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("Missing Months Diagnosis Report")
    lines.append(f"sales_dir: {SALES_DIR.as_posix()}")
    lines.append(f"merged_csv: {MERGED_CSV.as_posix()}")
    lines.append(f"merge_log: {MERGE_LOG.as_posix()}")
    lines.append("")

    # 1) sales_YYYY_MM folders
    month_dirs = []
    if SALES_DIR.exists():
        for p in sorted(SALES_DIR.iterdir()):
            if p.is_dir():
                month_key = month_from_sales_dir_name(p.name)
                if month_key:
                    month_dirs.append((month_key, p))

    lines.append("[1) sales_YYYY_MM Folder List]")
    if month_dirs:
        for month_key, p in month_dirs:
            lines.append(f"{month_key} -> {p.relative_to(BASE_DIR).as_posix()}")
    else:
        lines.append("No sales_YYYY_MM folders found.")
    lines.append("")

    # 2) file count per month folder
    month_file_count: dict[str, int] = {}
    lines.append("[2) File Count Per Month Folder]")
    for month_key, p in month_dirs:
        cnt = len([f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in EXCEL_EXTENSIONS])
        month_file_count[month_key] = cnt
        lines.append(f"{month_key}: {cnt}")
    lines.append("")

    # 3) success/failure per month based on merge log
    failed_rel_paths: set[str] = set()
    if MERGE_LOG.exists():
        failed_rel_paths = parse_failed_files_from_log(MERGE_LOG.read_text(encoding="utf-8", errors="replace"))

    month_failed_count = defaultdict(int)
    for rel in failed_rel_paths:
        m = re.search(r"data/raw/sales/(sales_\d{4}_\d{2})/", rel)
        if m:
            month_key = month_from_sales_dir_name(m.group(1))
            if month_key:
                month_failed_count[month_key] += 1

    lines.append("[3) Merge Success/Fail Per Month (based on merge_sales_log.txt)]")
    for month_key, _ in month_dirs:
        total = month_file_count.get(month_key, 0)
        failed = month_failed_count.get(month_key, 0)
        success = max(total - failed, 0)
        status = "ALL_SUCCESS"
        if failed > 0 and success > 0:
            status = "PARTIAL_FAIL"
        elif failed == total and total > 0:
            status = "ALL_FAIL"
        lines.append(f"{month_key}: total={total}, success={success}, failed={failed}, status={status}")
    lines.append("")

    # 4) monthly row count from merged csv
    merged_month_rows: dict[str, int] = {}
    lines.append("[4) Monthly Row Count in daily_sales_raw.csv]")
    if MERGED_CSV.exists():
        df = pd.read_csv(MERGED_CSV, usecols=["date"], low_memory=False)
        d = pd.to_datetime(df["date"], errors="coerce")
        month_counts = (
            d.dropna().dt.strftime("%Y-%m").value_counts().sort_index()
        )
        for month, cnt in month_counts.items():
            merged_month_rows[str(month)] = int(cnt)
            lines.append(f"{month}: {int(cnt)}")
    else:
        lines.append("Merged CSV not found.")
    lines.append("")

    # 5) months in raw folders but missing in merged csv
    raw_months = [m for m, _ in month_dirs]
    missing_months = [m for m in raw_months if m not in merged_month_rows]

    lines.append("[5) Months Existing in Raw Folder but Missing in daily_sales_raw.csv]")
    if missing_months:
        for m in missing_months:
            lines.append(m)
    else:
        lines.append("None")
    lines.append("")

    # extra quick summary
    lines.append("[Summary]")
    lines.append(f"raw_month_count: {len(raw_months)}")
    lines.append(f"merged_month_count: {len(merged_month_rows)}")
    lines.append(f"missing_month_count: {len(missing_months)}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Report saved: {REPORT_PATH}")
    print(f"Raw month count: {len(raw_months)}")
    print(f"Merged month count: {len(merged_month_rows)}")
    print(f"Missing month count: {len(missing_months)}")


if __name__ == "__main__":
    main()
