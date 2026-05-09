from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CSV = BASE_DIR / "data" / "processed" / "daily_sales_raw_v2.csv"
REP_MASTER_CSV = BASE_DIR / "data" / "processed" / "product_master_representative.csv"

OUTPUT_CSV = BASE_DIR / "data" / "processed" / "daily_sales_with_product.csv"
UNMATCHED_CSV = BASE_DIR / "outputs" / "reports" / "unmatched_after_merge.csv"
LOG_PATH = BASE_DIR / "outputs" / "reports" / "daily_sales_product_merge_log.txt"


def normalize_product_name(value: object) -> str:
    text = str(value)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    UNMATCHED_CSV.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_CSV.exists():
        raise FileNotFoundError(f"Sales file not found: {SALES_CSV}")
    if not REP_MASTER_CSV.exists():
        raise FileNotFoundError(f"Representative master file not found: {REP_MASTER_CSV}")

    sales = pd.read_csv(SALES_CSV, low_memory=False)
    rep = pd.read_csv(REP_MASTER_CSV, low_memory=False)

    required_sales = {"date", "category", "product_name", "sales_qty", "purchase_qty"}
    missing_sales = required_sales - set(sales.columns)
    if missing_sales:
        raise KeyError(f"Missing columns in sales file: {sorted(missing_sales)}")

    required_rep = {"product_name_norm", "representative_plu_code", "representative_category"}
    missing_rep = required_rep - set(rep.columns)
    if missing_rep:
        raise KeyError(f"Missing columns in representative master file: {sorted(missing_rep)}")

    # 2) build normalized name in sales
    sales["product_name_norm"] = sales["product_name"].map(normalize_product_name)

    # Ensure right table key is normalized as string
    rep["product_name_norm"] = rep["product_name_norm"].astype(str).map(normalize_product_name)

    # 3) left merge
    merged = sales.merge(
        rep[["product_name_norm", "representative_plu_code", "representative_category"]],
        on="product_name_norm",
        how="left",
    )

    # 4) keep columns
    merged = merged[
        [
            "date",
            "category",
            "product_name",
            "product_name_norm",
            "sales_qty",
            "purchase_qty",
            "representative_plu_code",
            "representative_category",
        ]
    ].copy()

    # 5) rename columns
    merged = merged.rename(
        columns={
            "representative_plu_code": "plu_code",
            "representative_category": "product_category",
        }
    )

    # 6) match stats
    matched_rows = int(merged["plu_code"].notna().sum())
    unmatched_rows = int(merged["plu_code"].isna().sum())
    total_rows = len(merged)
    match_rate = (matched_rows / total_rows * 100.0) if total_rows else 0.0

    # 7) top 100 unmatched product names
    unmatched_top100 = (
        merged[merged["plu_code"].isna()]
        .groupby("product_name_norm", as_index=False)
        .agg(
            row_count=("product_name_norm", "size"),
            sample_product_name=("product_name", "first"),
        )
        .query("product_name_norm != ''")
        .sort_values(["row_count", "product_name_norm"], ascending=[False, True])
        .head(100)
        .reset_index(drop=True)
    )
    unmatched_top100.to_csv(UNMATCHED_CSV, index=False, encoding="utf-8-sig")

    # 8) final save
    merged.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 9) save log
    log_lines: list[str] = []
    log_lines.append("Daily Sales + Product Master Merge Log")
    log_lines.append(f"sales_csv: {SALES_CSV.as_posix()}")
    log_lines.append(f"representative_master_csv: {REP_MASTER_CSV.as_posix()}")
    log_lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    log_lines.append(f"unmatched_csv: {UNMATCHED_CSV.as_posix()}")
    log_lines.append("")
    log_lines.append(f"total_rows: {total_rows}")
    log_lines.append(f"plu_code_matched_rows: {matched_rows}")
    log_lines.append(f"plu_code_unmatched_rows: {unmatched_rows}")
    log_lines.append(f"match_rate_percent: {match_rate:.2f}")
    log_lines.append(f"unmatched_unique_product_name_norm_top100_count: {len(unmatched_top100)}")

    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")

    print(f"Saved merged file: {OUTPUT_CSV}")
    print(f"Saved log: {LOG_PATH}")
    print(f"Saved unmatched top100: {UNMATCHED_CSV}")
    print(f"Total rows: {total_rows}")
    print(f"Matched rows: {matched_rows}")
    print(f"Unmatched rows: {unmatched_rows}")
    print(f"Match rate (%): {match_rate:.2f}")


if __name__ == "__main__":
    main()
