"""Preprocess — match sales with product master, build final dataset.

Consolidates logic from legacy scripts 14, 16, 17.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Paths
from ..utils.io import safe_read_csv, safe_save_csv
from ..utils.report import write_report


def match_sales_with_product(
    sales_csv: Path | None = None,
    product_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Left-join daily sales with product master on product_name.

    Produces ``daily_sales_with_product.csv``.
    """
    sales_csv = sales_csv or Paths.DAILY_SALES_RAW
    product_csv = product_csv or Paths.PRODUCT_MASTER
    output_csv = output_csv or Paths.SALES_WITH_PRODUCT

    sales = safe_read_csv(sales_csv)
    product = safe_read_csv(product_csv)

    # normalise join keys
    sales["product_name"] = sales["product_name"].astype(str).str.strip()
    product["product_name"] = product["product_name"].astype(str).str.strip()

    # keep only needed cols from product
    prod_cols = ["product_name", "plu_code", "product_category"]
    prod_cols = [c for c in prod_cols if c in product.columns]
    product_dedup = product[prod_cols].drop_duplicates(subset=["product_name"], keep="first")

    merged = sales.merge(product_dedup, on="product_name", how="left")

    safe_save_csv(merged, output_csv)
    matched = merged["plu_code"].notna().sum()
    print(f"Sales×Product: {len(merged)} rows, {matched} matched → {output_csv.name}")
    return merged


def build_final_sales_dataset(
    input_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Clean, deduplicate, and produce ``final_sales_dataset.csv``.

    Based on legacy 17_build_final_sales_dataset.
    """
    improved = Paths.SALES_WITH_PRODUCT_IMPROVED
    default = Paths.SALES_WITH_PRODUCT
    input_csv = input_csv or (improved if improved.exists() else default)
    output_csv = output_csv or Paths.FINAL_SALES
    report_path = Paths.REPORTS_DIR / "final_sales_dataset_report.txt"

    df = safe_read_csv(input_csv)

    required = {"date", "plu_code", "product_name", "product_category", "sales_qty", "purchase_qty"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    original = len(df)

    # keep only matched rows
    work = df[df["plu_code"].notna()].copy()
    work["plu_code"] = work["plu_code"].astype(str).str.strip()
    work = work[(work["plu_code"] != "") & (work["plu_code"].str.lower() != "nan")]

    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work[work["date"].notna()].copy()
    work["sales_qty"] = pd.to_numeric(work["sales_qty"], errors="coerce")
    work["purchase_qty"] = pd.to_numeric(work["purchase_qty"], errors="coerce")
    work = work[work["sales_qty"].notna() & work["purchase_qty"].notna()].copy()

    # remove negative
    work = work[(work["sales_qty"] >= 0) & (work["purchase_qty"] >= 0)].copy()

    # deduplicate
    work["product_name"] = work["product_name"].astype(str)
    work["product_category"] = work["product_category"].astype(str)
    final = (
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

    save = final.copy()
    save["date"] = save["date"].dt.strftime("%Y-%m-%d")
    save = save[["date", "plu_code", "product_name", "product_category", "sales_qty", "purchase_qty"]]
    safe_save_csv(save, output_csv)

    lines = [
        "Final Sales Dataset Report",
        f"input: {input_csv.as_posix()}",
        f"original_rows: {original}",
        f"final_rows: {len(final)}",
        f"date: {final['date'].min()} ~ {final['date'].max()}",
        f"plu_unique: {final['plu_code'].nunique()}",
    ]
    write_report(report_path, lines)
    print(f"Final dataset: {len(final)} rows → {output_csv.name}")
    return final
