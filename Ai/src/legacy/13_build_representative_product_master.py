from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "data" / "processed" / "product_master.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "product_master_representative.csv"
LOG_PATH = BASE_DIR / "outputs" / "reports" / "product_master_representative_log.txt"


def normalize_product_name(value: object) -> str:
    text = str(value)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    required = {"product_name", "plu_code", "product_category"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    # 2) normalize product name
    work = df.copy()
    work["product_name_norm"] = work["product_name"].map(normalize_product_name)
    work["plu_code"] = work["plu_code"].astype(str).str.strip()
    work["product_category"] = work["product_category"].astype(str).str.strip()

    # Remove empty keys.
    work = work[(work["product_name_norm"] != "") & (work["plu_code"] != "")]

    # 3) choose representative plu_code by highest frequency per normalized product name.
    # Tie-breaker: lexicographically smallest plu_code for deterministic output.
    plu_freq = (
        work.groupby(["product_name_norm", "plu_code"], as_index=False)
        .size()
        .rename(columns={"size": "plu_freq"})
    )

    plu_freq_sorted = plu_freq.sort_values(
        ["product_name_norm", "plu_freq", "plu_code"],
        ascending=[True, False, True],
    )
    top_plu = plu_freq_sorted.drop_duplicates(subset=["product_name_norm"], keep="first")

    # representative_category: category most frequently associated with representative plu_code.
    category_freq = (
        work.groupby(["product_name_norm", "plu_code", "product_category"], as_index=False)
        .size()
        .rename(columns={"size": "category_freq"})
    )
    category_freq_sorted = category_freq.sort_values(
        ["product_name_norm", "plu_code", "category_freq", "product_category"],
        ascending=[True, True, False, True],
    )
    top_category = category_freq_sorted.drop_duplicates(
        subset=["product_name_norm", "plu_code"], keep="first"
    )

    candidate_plu_count = (
        work.groupby("product_name_norm", as_index=False)["plu_code"]
        .nunique()
        .rename(columns={"plu_code": "candidate_plu_count"})
    )

    rep = top_plu.merge(
        top_category[["product_name_norm", "plu_code", "product_category"]],
        on=["product_name_norm", "plu_code"],
        how="left",
    ).merge(candidate_plu_count, on="product_name_norm", how="left")

    rep = rep.rename(
        columns={
            "plu_code": "representative_plu_code",
            "product_category": "representative_category",
        }
    )
    rep = rep[
        [
            "product_name_norm",
            "representative_plu_code",
            "representative_category",
            "candidate_plu_count",
        ]
    ].sort_values("product_name_norm").reset_index(drop=True)

    rep.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    multi_candidate_count = int((rep["candidate_plu_count"] > 1).sum())

    log_lines: list[str] = []
    log_lines.append("Product Master Representative Build Log")
    log_lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    log_lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    log_lines.append(f"input_rows: {len(df)}")
    log_lines.append(f"normalized_unique_product_names: {rep['product_name_norm'].nunique()}")
    log_lines.append(f"output_rows: {len(rep)}")
    log_lines.append(f"names_with_multiple_candidate_plu: {multi_candidate_count}")

    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")

    print(f"Saved representative table: {OUTPUT_CSV}")
    print(f"Saved log: {LOG_PATH}")
    print(f"Output rows: {len(rep)}")
    print(f"Names with multiple candidate PLU: {multi_candidate_count}")


if __name__ == "__main__":
    main()
