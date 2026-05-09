from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

# Prefer improved merge file if it exists in processed path, otherwise fallback.
IMPROVED_MERGE_CSV = BASE_DIR / "data" / "processed" / "daily_sales_with_product_improved.csv"
DEFAULT_MERGE_CSV = BASE_DIR / "data" / "processed" / "daily_sales_with_product.csv"

OUTPUT_CSV = BASE_DIR / "data" / "processed" / "final_sales_dataset.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "final_sales_dataset_report.txt"


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    input_csv = IMPROVED_MERGE_CSV if IMPROVED_MERGE_CSV.exists() else DEFAULT_MERGE_CSV
    if not input_csv.exists():
        raise FileNotFoundError(f"Input merge file not found: {input_csv}")

    df = pd.read_csv(input_csv, low_memory=False)

    required = {"date", "plu_code", "product_name", "product_category", "sales_qty", "purchase_qty"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    original_rows = len(df)

    # 2) keep matched rows only
    work = df[df["plu_code"].notna()].copy()
    work["plu_code"] = work["plu_code"].astype(str).str.strip()
    work = work[(work["plu_code"] != "") & (work["plu_code"].str.lower() != "nan")]
    matched_rows = len(work)

    # 3) convert date
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work[work["date"].notna()].copy()

    # 4) numeric conversion
    work["sales_qty"] = pd.to_numeric(work["sales_qty"], errors="coerce")
    work["purchase_qty"] = pd.to_numeric(work["purchase_qty"], errors="coerce")
    work = work[work["sales_qty"].notna() & work["purchase_qty"].notna()].copy()

    # 5) remove negative outliers
    before_outlier_filter = len(work)
    work = work[(work["sales_qty"] >= 0) & (work["purchase_qty"] >= 0)].copy()
    removed_negative_rows = before_outlier_filter - len(work)

    # Keep representative product info per (date, plu_code) using first non-null values.
    work["product_name"] = work["product_name"].astype(str)
    work["product_category"] = work["product_category"].astype(str)

    # 6) deduplicate by date, plu_code with summed quantities
    pre_dedup_rows = len(work)
    final_df = (
        work.groupby(["date", "plu_code"], as_index=False)
        .agg(
            product_name=("product_name", "first"),
            product_category=("product_category", "first"),
            sales_qty=("sales_qty", "sum"),
            purchase_qty=("purchase_qty", "sum"),
        )
        .sort_values(["date", "plu_code"])
        .reset_index(drop=True)
    )
    dedup_removed_rows = pre_dedup_rows - len(final_df)

    # 7) final columns order
    final_df = final_df[["date", "plu_code", "product_name", "product_category", "sales_qty", "purchase_qty"]]

    # Save with ISO date string
    final_save = final_df.copy()
    final_save["date"] = final_save["date"].dt.strftime("%Y-%m-%d")
    final_save.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 10) report
    lines: list[str] = []
    lines.append("Final Sales Dataset Report")
    lines.append(f"input_csv: {input_csv.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append(f"original_rows: {original_rows}")
    lines.append(f"rows_after_plu_matched_filter: {matched_rows}")
    lines.append(f"rows_after_negative_filter: {len(work)}")
    lines.append(f"removed_negative_rows: {removed_negative_rows}")
    lines.append(f"rows_before_dedup_grouping: {pre_dedup_rows}")
    lines.append(f"rows_after_dedup_grouping: {len(final_df)}")
    lines.append(f"dedup_removed_rows: {dedup_removed_rows}")
    lines.append("")
    lines.append(f"final_rows: {len(final_df)}")
    lines.append(f"date_min: {final_df['date'].min()}")
    lines.append(f"date_max: {final_df['date'].max()}")
    lines.append(f"plu_code_unique_count: {final_df['plu_code'].nunique()}")
    lines.append(f"product_category_unique_count: {final_df['product_category'].nunique()}")
    lines.append("")
    lines.append("[sales_qty stats]")
    lines.append(f"min: {final_df['sales_qty'].min()}")
    lines.append(f"max: {final_df['sales_qty'].max()}")
    lines.append(f"mean: {final_df['sales_qty'].mean()}")
    lines.append(f"median: {final_df['sales_qty'].median()}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved final dataset: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Final rows: {len(final_df)}")
    print(f"Date range: {final_df['date'].min()} ~ {final_df['date'].max()}")
    print(f"PLU unique: {final_df['plu_code'].nunique()}")
    print(f"Category unique: {final_df['product_category'].nunique()}")
    print(f"Dedup removed rows: {dedup_removed_rows}")


if __name__ == "__main__":
    main()
