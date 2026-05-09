from __future__ import annotations

from math import ceil
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction.csv"
OUTPUT_CSV = BASE_DIR / "outputs" / "reports" / "order_recommendation.csv"
SUMMARY_TXT = BASE_DIR / "outputs" / "reports" / "order_recommendation_summary.txt"

SAFETY_FACTOR = 1.2


def calc_recommended_order(pred: float, safety_factor: float) -> int:
    if pred <= 0:
        return 0
    return int(ceil(pred * safety_factor))


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    required_cols = [
        "base_date",
        "predict_date",
        "plu_code",
        "product_name",
        "product_category",
        "predicted_sales_qty",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    df["predicted_sales_qty"] = pd.to_numeric(df["predicted_sales_qty"], errors="coerce").fillna(0)
    df["recommended_order_qty"] = df["predicted_sales_qty"].map(
        lambda x: calc_recommended_order(float(x), SAFETY_FACTOR)
    )
    df["recommended_order_qty"] = df["recommended_order_qty"].astype(int)

    out_df = df[
        [
            "base_date",
            "predict_date",
            "plu_code",
            "product_name",
            "product_category",
            "predicted_sales_qty",
            "recommended_order_qty",
        ]
    ].copy()

    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    total_products = len(out_df)
    total_order_qty = int(out_df["recommended_order_qty"].sum())
    avg_order_qty = float(out_df["recommended_order_qty"].mean()) if total_products else 0.0

    top20 = out_df.sort_values("recommended_order_qty", ascending=False).head(20)

    lines: list[str] = []
    lines.append("Order Recommendation Summary")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append(f"safety_factor: {SAFETY_FACTOR}")
    lines.append("")
    lines.append(f"total_products: {total_products}")
    lines.append(f"total_recommended_order_qty: {total_order_qty}")
    lines.append(f"average_recommended_order_qty: {avg_order_qty}")
    lines.append("")
    lines.append("[Top 20 Recommended Order Qty]")
    if top20.empty:
        lines.append("None")
    else:
        lines.append(
            top20[
                [
                    "plu_code",
                    "product_name",
                    "product_category",
                    "predicted_sales_qty",
                    "recommended_order_qty",
                ]
            ].to_string(index=False)
        )

    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved recommendation csv: {OUTPUT_CSV}")
    print(f"Saved summary report: {SUMMARY_TXT}")
    print(f"Total products: {total_products}")
    print(f"Total recommended qty: {total_order_qty}")
    print(f"Average recommended qty: {avg_order_qty}")


if __name__ == "__main__":
    main()
