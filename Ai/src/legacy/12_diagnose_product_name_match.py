from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CSV = BASE_DIR / "data" / "processed" / "daily_sales_raw_v2.csv"
MASTER_CSV = BASE_DIR / "data" / "processed" / "product_master.csv"

REPORT_TXT = BASE_DIR / "outputs" / "reports" / "product_name_match_diagnosis.txt"
UNMATCHED_CSV = BASE_DIR / "outputs" / "reports" / "unmatched_sales_product_names.csv"
DUP_MASTER_CSV = BASE_DIR / "outputs" / "reports" / "duplicated_product_names_in_master.csv"


def normalize_product_name(value: object) -> str:
    text = str(value)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def main() -> None:
    REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("Product Name Match Diagnosis Report")
    lines.append(f"sales_csv: {SALES_CSV.as_posix()}")
    lines.append(f"master_csv: {MASTER_CSV.as_posix()}")
    lines.append("")

    if not SALES_CSV.exists():
        lines.append("ERROR: daily_sales_raw_v2.csv does not exist.")
        REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_TXT}")
        return
    if not MASTER_CSV.exists():
        lines.append("ERROR: product_master.csv does not exist.")
        REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved: {REPORT_TXT}")
        return

    sales = pd.read_csv(SALES_CSV, low_memory=False)
    master = pd.read_csv(MASTER_CSV, low_memory=False)

    if "product_name" not in sales.columns:
        raise KeyError("'product_name' column not found in sales data.")
    if "product_name" not in master.columns or "plu_code" not in master.columns:
        raise KeyError("'product_name' or 'plu_code' column not found in product master.")

    # 3) normalized column
    sales["product_name_norm"] = sales["product_name"].map(normalize_product_name)
    master["product_name_norm"] = master["product_name"].map(normalize_product_name)

    sales_unique = (
        sales[["product_name_norm"]]
        .dropna()
        .drop_duplicates()
        .query("product_name_norm != ''")
        .copy()
    )
    master_unique = (
        master[["product_name_norm"]]
        .dropna()
        .drop_duplicates()
        .query("product_name_norm != ''")
        .copy()
    )

    # 4) duplicates in master by normalized product name
    master_name_dup_count = int(master.duplicated(subset=["product_name_norm"]).sum())

    # 8) names mapping to multiple plu_code
    master_multi_plu = (
        master.dropna(subset=["product_name_norm", "plu_code"])
        .assign(
            product_name_norm=lambda d: d["product_name_norm"].astype(str),
            plu_code=lambda d: d["plu_code"].astype(str).str.strip(),
        )
        .groupby("product_name_norm", as_index=False)
        .agg(
            plu_code_unique_count=("plu_code", "nunique"),
            plu_code_sample=("plu_code", lambda s: " | ".join(sorted(pd.unique(s.dropna()))[:10])),
        )
    )
    master_multi_plu = master_multi_plu[master_multi_plu["plu_code_unique_count"] > 1].sort_values(
        ["plu_code_unique_count", "product_name_norm"], ascending=[False, True]
    )
    master_multi_plu.to_csv(DUP_MASTER_CSV, index=False, encoding="utf-8-sig")

    # 5,6) match ratio and success/fail counts
    master_name_set = set(master_unique["product_name_norm"].tolist())
    sales_unique["is_matched"] = sales_unique["product_name_norm"].isin(master_name_set)

    matched_count = int(sales_unique["is_matched"].sum())
    unmatched_count = int((~sales_unique["is_matched"]).sum())
    total_sales_unique = int(len(sales_unique))
    match_ratio = (matched_count / total_sales_unique * 100.0) if total_sales_unique else 0.0

    # 7) top 100 unmatched names by frequency in sales
    sales_name_freq = (
        sales.assign(product_name_norm=sales["product_name_norm"].astype(str))
        .groupby("product_name_norm", as_index=False)
        .agg(
            sales_row_count=("product_name_norm", "size"),
            sample_product_name=("product_name", "first"),
        )
    )
    unmatched_top100 = (
        sales_name_freq[~sales_name_freq["product_name_norm"].isin(master_name_set)]
        .query("product_name_norm != ''")
        .sort_values(["sales_row_count", "product_name_norm"], ascending=[False, True])
        .head(100)
        .reset_index(drop=True)
    )
    unmatched_top100.to_csv(UNMATCHED_CSV, index=False, encoding="utf-8-sig")

    lines.append("[1) Basic Counts]")
    lines.append(f"sales_rows: {len(sales)}")
    lines.append(f"master_rows: {len(master)}")
    lines.append(f"sales_unique_product_name_norm: {total_sales_unique}")
    lines.append(f"master_unique_product_name_norm: {len(master_unique)}")
    lines.append("")

    lines.append("[2) Product Master Duplicate Check]")
    lines.append(f"duplicate_rows_by_product_name_norm_in_master: {master_name_dup_count}")
    lines.append(f"product_name_norm_with_multiple_plu_code_count: {len(master_multi_plu)}")
    lines.append(f"saved_csv: {DUP_MASTER_CSV.as_posix()}")
    lines.append("")

    lines.append("[3) Match Result (sales unique names vs master unique names)]")
    lines.append(f"matched_unique_product_names: {matched_count}")
    lines.append(f"unmatched_unique_product_names: {unmatched_count}")
    lines.append(f"match_ratio_percent: {match_ratio:.2f}")
    lines.append(f"saved_unmatched_csv: {UNMATCHED_CSV.as_posix()}")
    lines.append("")

    lines.append("[4) Top 20 Unmatched Product Names]")
    if unmatched_top100.empty:
        lines.append("None")
    else:
        lines.append(unmatched_top100.head(20).to_string(index=False))

    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Report saved: {REPORT_TXT}")
    print(f"Unmatched top100 saved: {UNMATCHED_CSV}")
    print(f"Duplicated names in master saved: {DUP_MASTER_CSV}")
    print(f"Matched unique names: {matched_count}")
    print(f"Unmatched unique names: {unmatched_count}")
    print(f"Match ratio (%): {match_ratio:.2f}")


if __name__ == "__main__":
    main()
