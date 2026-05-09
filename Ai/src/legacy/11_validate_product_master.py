from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "product_master.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "product_master_validation_report.txt"


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    lines.append("Product Master Validation Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append("")

    if not INPUT_CSV.exists():
        lines.append("ERROR: input CSV does not exist.")
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    required_cols = ["product_name", "plu_code", "product_category"]
    missing_required = [c for c in required_cols if c not in df.columns]
    if missing_required:
        lines.append(f"ERROR: missing required columns: {missing_required}")
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_PATH}")
        return

    lines.append("[1) Basic Info]")
    lines.append(f"total_rows: {len(df)}")
    lines.append(f"columns: {list(df.columns)}")
    lines.append(f"product_name_unique_count: {df['product_name'].nunique(dropna=True)}")
    lines.append(f"plu_code_unique_count: {df['plu_code'].nunique(dropna=True)}")
    category_values = sorted(df["product_category"].dropna().astype(str).unique().tolist())
    lines.append(f"product_category_unique_values: {category_values}")
    lines.append("")

    lines.append("[2) Missing Values]")
    lines.append(f"product_name_missing: {int(df['product_name'].isna().sum())}")
    lines.append(f"plu_code_missing: {int(df['plu_code'].isna().sum())}")
    lines.append(f"product_category_missing: {int(df['product_category'].isna().sum())}")
    lines.append("")

    lines.append("[3) Duplicate Check]")
    dup_name_plu = int(df.duplicated(subset=["product_name", "plu_code"]).sum())
    dup_name_only = int(df.duplicated(subset=["product_name"]).sum())
    lines.append(f"duplicate_count_by_product_name_plu_code: {dup_name_plu}")
    lines.append(f"duplicate_count_by_product_name_only: {dup_name_only}")
    lines.append("")

    lines.append("[4) Top 20 Rows]")
    top20 = df.head(20).copy()
    lines.append(top20.to_string(index=False))

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Report saved: {REPORT_PATH}")
    print(f"Total rows: {len(df)}")
    print(f"Duplicate(product_name, plu_code): {dup_name_plu}")
    print(f"Duplicate(product_name only): {dup_name_only}")


if __name__ == "__main__":
    main()
