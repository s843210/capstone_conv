from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "daily_sales_raw.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "daily_sales_validation_report.txt"


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report_lines: list[str] = []
    report_lines.append("Daily Sales Raw Validation Report")
    report_lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    report_lines.append("")

    if not INPUT_CSV.exists():
        report_lines.append("ERROR: input CSV does not exist.")
        REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    # Date parsing for range checks and daily counts.
    date_series = pd.to_datetime(df["date"], errors="coerce")

    # Ensure numeric sales_qty metrics are robust.
    sales_series = pd.to_numeric(df["sales_qty"], errors="coerce")

    report_lines.append("[1) Basic Info]")
    report_lines.append(f"total_rows: {len(df)}")
    report_lines.append(f"columns: {list(df.columns)}")
    report_lines.append(f"date_min: {date_series.min()}")
    report_lines.append(f"date_max: {date_series.max()}")
    report_lines.append(f"category_unique_values: {sorted(df['category'].dropna().astype(str).unique().tolist())}")
    report_lines.append(f"product_name_unique_count: {df['product_name'].nunique(dropna=True)}")
    report_lines.append("")

    report_lines.append("[2) Missing Values]")
    missing_counts = df.isna().sum()
    for col, cnt in missing_counts.items():
        report_lines.append(f"{col}: {int(cnt)}")
    report_lines.append("")

    report_lines.append("[3) Duplicate Check]")
    dup_count = int(df.duplicated(subset=["date", "category", "product_name"]).sum())
    report_lines.append(f"duplicate_count_by_date_category_product_name: {dup_count}")
    report_lines.append("")

    report_lines.append("[4) sales_qty Check]")
    report_lines.append(f"sales_qty_min: {sales_series.min()}")
    report_lines.append(f"sales_qty_max: {sales_series.max()}")
    report_lines.append(f"sales_qty_mean: {sales_series.mean()}")
    report_lines.append(f"sales_qty_negative_rows: {int((sales_series < 0).sum())}")
    report_lines.append(f"sales_qty_zero_rows: {int((sales_series == 0).sum())}")
    report_lines.append("")

    report_lines.append("[5) Rows Per Date]")
    valid_date_df = df.copy()
    valid_date_df["date_parsed"] = date_series
    valid_date_df = valid_date_df[valid_date_df["date_parsed"].notna()]

    date_counts = (
        valid_date_df.groupby(valid_date_df["date_parsed"].dt.strftime("%Y-%m-%d"))
        .size()
        .reset_index(name="row_count")
        .sort_values("date_parsed")
    )
    for _, row in date_counts.iterrows():
        report_lines.append(f"{row['date_parsed']}: {int(row['row_count'])}")

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Report saved: {REPORT_PATH}")
    print(f"Total rows: {len(df)}")
    print(f"Date range: {date_series.min()} ~ {date_series.max()}")
    print(f"Duplicate rows (date, category, product_name): {dup_count}")


if __name__ == "__main__":
    main()
