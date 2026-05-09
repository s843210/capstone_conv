from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "daily_sales_raw.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "invalid_date_diagnosis.txt"


def extract_path_parts(source_file: str) -> tuple[str, str, str]:
    # Expected pattern:
    # data/raw/sales/sales_YYYY_MM/<date_folder_optional>/<file_name>
    sales_month = ""
    date_folder = ""
    file_name = ""

    if not isinstance(source_file, str):
        return sales_month, date_folder, file_name

    norm = source_file.replace("\\", "/")
    parts = [p for p in norm.split("/") if p]
    if parts:
        file_name = parts[-1]

    for i, part in enumerate(parts):
        if re.fullmatch(r"sales_\d{4}_\d{2}", part):
            sales_month = part
            if i + 1 < len(parts) - 1:
                date_folder = parts[i + 1]
            break

    return sales_month, date_folder, file_name


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("Invalid Date Diagnosis Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append("")

    if not INPUT_CSV.exists():
        lines.append("ERROR: input CSV does not exist.")
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    df = pd.read_csv(INPUT_CSV, low_memory=False, dtype={"date": "string", "source_file": "string"})
    if "date" not in df.columns:
        lines.append("ERROR: 'date' column not found.")
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    # 1) unique date values
    date_raw = df["date"].astype("string")
    unique_dates = sorted(date_raw.dropna().unique().tolist())

    # 2) NaT diagnosis
    parsed = pd.to_datetime(date_raw, errors="coerce")
    nat_mask = parsed.isna()
    nat_count = int(nat_mask.sum())
    nat_raw_values = sorted(date_raw[nat_mask].dropna().unique().tolist())

    lines.append("[1) Date Raw Unique Values]")
    lines.append(f"unique_date_count: {len(unique_dates)}")
    for d in unique_dates:
        lines.append(str(d))
    lines.append("")

    lines.append("[2) to_datetime(..., errors='coerce') Result]")
    lines.append(f"total_rows: {len(df)}")
    lines.append(f"nat_count: {nat_count}")
    lines.append("nat_raw_date_values:")
    if nat_raw_values:
        for d in nat_raw_values:
            lines.append(f"- {d}")
    else:
        lines.append("- None")
    lines.append("")

    # 3,4) source_file samples for NaT rows + parsed path pieces
    lines.append("[3) NaT Rows Source File Samples]")
    if nat_count > 0:
        nat_df = df.loc[nat_mask, ["date", "source_file"]].copy()
        nat_df["source_file"] = nat_df["source_file"].fillna("")

        # Keep unique source files for readable sampling.
        nat_unique_sources = nat_df.drop_duplicates(subset=["source_file"]).head(100)
        lines.append(f"sample_source_file_count: {len(nat_unique_sources)} (max 100)")

        lines.append("[4) Extracted Path Parts From NaT Source Files]")
        for _, row in nat_unique_sources.iterrows():
            raw_date = str(row["date"])
            source_file = str(row["source_file"])
            sales_month, date_folder, file_name = extract_path_parts(source_file)
            lines.append(f"date_raw: {raw_date}")
            lines.append(f"source_file: {source_file}")
            lines.append(f"sales_month_folder: {sales_month}")
            lines.append(f"date_folder: {date_folder}")
            lines.append(f"file_name: {file_name}")
            lines.append("---")
    else:
        lines.append("No NaT rows found.")
    lines.append("")

    # 5) min/max on valid parsed dates
    valid_dates = parsed.dropna()
    lines.append("[5) Valid Parsed Date Range]")
    if not valid_dates.empty:
        lines.append(f"valid_date_min: {valid_dates.min()}")
        lines.append(f"valid_date_max: {valid_dates.max()}")
    else:
        lines.append("No valid parsed dates.")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Report saved: {REPORT_PATH}")
    print(f"Total rows: {len(df)}")
    print(f"NaT count: {nat_count}")
    if not valid_dates.empty:
        print(f"Valid date range: {valid_dates.min()} ~ {valid_dates.max()}")


if __name__ == "__main__":
    main()
