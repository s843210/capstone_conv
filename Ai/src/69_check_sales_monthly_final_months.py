from __future__ import annotations

from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_MONTHLY_DIR = BASE_DIR / "data" / "raw" / "sales_monthly"
OUTPUT_REPORT = BASE_DIR / "outputs" / "reports" / "sales_monthly_final_month_check.txt"
START_MONTH = "2024-03"
END_MONTH = "2026-04"
TARGET_EXT = {".xlsx", ".xls", ".csv"}


def build_expected_months(start_ym: str, end_ym: str) -> List[str]:
    sy, sm = map(int, start_ym.split("-"))
    ey, em = map(int, end_ym.split("-"))
    out: List[str] = []
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


def main() -> None:
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_MONTHLY_DIR.exists():
        raise FileNotFoundError(f"Directory not found: {SALES_MONTHLY_DIR}")

    month_dirs = sorted(
        p for p in SALES_MONTHLY_DIR.iterdir()
        if p.is_dir() and p.name.isdigit() and len(p.name) == 6
    )

    month_file_counts: Dict[str, int] = {}
    for d in month_dirs:
        ym = f"{d.name[:4]}-{d.name[4:6]}"
        cnt = sum(
            1 for f in d.rglob("*")
            if f.is_file() and f.suffix.lower() in TARGET_EXT
        )
        month_file_counts[ym] = cnt

    existing_months = sorted(month_file_counts.keys())
    expected_months = build_expected_months(START_MONTH, END_MONTH)
    missing_months = [m for m in expected_months if m not in existing_months]

    lines: List[str] = []
    lines.append("Sales Monthly Final Month Check")
    lines.append(f"target_directory: {SALES_MONTHLY_DIR.as_posix()}")
    lines.append(f"expected_range: {START_MONTH} ~ {END_MONTH}")
    lines.append("")
    lines.append(f"existing_months: {existing_months}")
    lines.append(f"missing_months: {missing_months if missing_months else 'None'}")
    lines.append("")
    lines.append("[monthly_file_count]")
    for ym in expected_months:
        lines.append(f"- {ym}: {month_file_counts.get(ym, 0)}")

    OUTPUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved report: {OUTPUT_REPORT}")
    print(f"Existing months: {len(existing_months)}")
    print(f"Missing months: {len(missing_months)}")


if __name__ == "__main__":
    main()
