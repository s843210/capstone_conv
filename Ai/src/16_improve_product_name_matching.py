from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_CSV = BASE_DIR / "data" / "processed" / "daily_sales_raw_v2.csv"
REP_MASTER_CSV = BASE_DIR / "data" / "processed" / "product_master_representative.csv"

OUT_REPORT = BASE_DIR / "outputs" / "reports" / "improved_product_name_match_report.txt"
OUT_UNMATCHED = BASE_DIR / "outputs" / "reports" / "unmatched_after_improved_norm.csv"

BASELINE_MATCH_RATE = 66.20


def normalize_product_name_improved(value: object) -> str:
    s = str(value)
    s = s.strip()
    s = re.sub(r"\s+", " ", s)

    # Remove parentheses and content inside.
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"\{[^}]*\}", " ", s)

    # Remove promotion-related tokens.
    promo_pattern = (
        r"(?:\b[12]\s*\+\s*1\b|증정|행사|덤|무료|프로모션|사은품|기획|한정|할인)"
    )
    s = re.sub(promo_pattern, " ", s, flags=re.IGNORECASE)

    # Replace special chars with space (keep Korean/English/digits).
    s = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", s)

    # Normalize spaces again and uppercase English.
    s = re.sub(r"\s+", " ", s).strip()
    s = s.upper()
    return s


def main() -> None:
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_CSV.exists():
        raise FileNotFoundError(f"Sales file not found: {SALES_CSV}")
    if not REP_MASTER_CSV.exists():
        raise FileNotFoundError(f"Representative master file not found: {REP_MASTER_CSV}")

    sales = pd.read_csv(SALES_CSV, low_memory=False)
    rep = pd.read_csv(REP_MASTER_CSV, low_memory=False)

    required_sales = {"product_name"}
    missing_sales = required_sales - set(sales.columns)
    if missing_sales:
        raise KeyError(f"Missing sales columns: {sorted(missing_sales)}")

    required_rep = {"product_name_norm", "representative_plu_code", "representative_category"}
    missing_rep = required_rep - set(rep.columns)
    if missing_rep:
        raise KeyError(f"Missing representative columns: {sorted(missing_rep)}")

    # 2) improved normalization on both sides
    sales["product_name_norm_improved"] = sales["product_name"].map(normalize_product_name_improved)
    rep["product_name_norm_improved"] = rep["product_name_norm"].map(normalize_product_name_improved)

    # Deduplicate rep key for stable merge
    rep_for_merge = rep[
        ["product_name_norm_improved", "representative_plu_code", "representative_category"]
    ].drop_duplicates(subset=["product_name_norm_improved"], keep="first")

    # 3) left merge
    merged = sales.merge(rep_for_merge, on="product_name_norm_improved", how="left")

    # 4) match stats
    total_rows = len(merged)
    matched_rows = int(merged["representative_plu_code"].notna().sum())
    unmatched_rows = int(merged["representative_plu_code"].isna().sum())
    match_rate = (matched_rows / total_rows * 100.0) if total_rows else 0.0

    # 5) compare with baseline
    diff = match_rate - BASELINE_MATCH_RATE

    # 6) unmatched top 100
    unmatched_top100 = (
        merged[merged["representative_plu_code"].isna()]
        .groupby("product_name_norm_improved", as_index=False)
        .agg(
            row_count=("product_name_norm_improved", "size"),
            sample_product_name=("product_name", "first"),
        )
        .query("product_name_norm_improved != ''")
        .sort_values(["row_count", "product_name_norm_improved"], ascending=[False, True])
        .head(100)
        .reset_index(drop=True)
    )
    unmatched_top100.to_csv(OUT_UNMATCHED, index=False, encoding="utf-8-sig")

    # 7) report
    lines: list[str] = []
    lines.append("Improved Product Name Match Report")
    lines.append(f"sales_csv: {SALES_CSV.as_posix()}")
    lines.append(f"representative_master_csv: {REP_MASTER_CSV.as_posix()}")
    lines.append(f"unmatched_output_csv: {OUT_UNMATCHED.as_posix()}")
    lines.append("")
    lines.append(f"total_rows: {total_rows}")
    lines.append(f"plu_code_matched_rows: {matched_rows}")
    lines.append(f"plu_code_unmatched_rows: {unmatched_rows}")
    lines.append(f"improved_match_rate_percent: {match_rate:.2f}")
    lines.append("")
    lines.append(f"baseline_match_rate_percent: {BASELINE_MATCH_RATE:.2f}")
    lines.append(f"match_rate_difference_percent_point: {diff:.2f}")
    lines.append("")
    lines.append("[Top 20 Unmatched After Improved Normalization]")
    if unmatched_top100.empty:
        lines.append("None")
    else:
        lines.append(unmatched_top100.head(20).to_string(index=False))

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved report: {OUT_REPORT}")
    print(f"Saved unmatched top100: {OUT_UNMATCHED}")
    print(f"Total rows: {total_rows}")
    print(f"Matched rows: {matched_rows}")
    print(f"Unmatched rows: {unmatched_rows}")
    print(f"Improved match rate (%): {match_rate:.2f}")
    print(f"Baseline match rate (%): {BASELINE_MATCH_RATE:.2f}")
    print(f"Difference (%p): {diff:.2f}")


if __name__ == "__main__":
    main()
