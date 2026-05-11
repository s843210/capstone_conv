from __future__ import annotations

import math
from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "outputs" / "reports" / "tomorrow_sales_prediction_monthly_v2_final.csv"
OUTPUT_CSV = BASE_DIR / "outputs" / "reports" / "order_recommendation_monthly_v2_final.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "order_recommendation_monthly_v2_final_report.txt"


def to_recommended_qty(pred: float) -> int:
    if pd.isna(pred) or pred <= 0:
        return 0
    qty = int(math.ceil(float(pred) * 1.2))
    if qty < 2:
        return 0
    return qty


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    required = [
        "base_date",
        "predict_date",
        "plu_code",
        "product_name",
        "product_category",
        "predicted_sales_qty",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    df["predicted_sales_qty"] = pd.to_numeric(df["predicted_sales_qty"], errors="coerce")
    df["recommended_order_qty"] = df["predicted_sales_qty"].map(to_recommended_qty).astype(int)

    out_cols = [
        "base_date",
        "predict_date",
        "plu_code",
        "product_name",
        "product_category",
        "predicted_sales_qty",
        "recommended_order_qty",
    ]
    out_df = df[out_cols].copy()
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    positive_orders = out_df[out_df["recommended_order_qty"] > 0].copy()
    if positive_orders.empty:
        qty_min = qty_max = qty_mean = qty_median = 0.0
    else:
        qty_min = float(positive_orders["recommended_order_qty"].min())
        qty_max = float(positive_orders["recommended_order_qty"].max())
        qty_mean = float(positive_orders["recommended_order_qty"].mean())
        qty_median = float(positive_orders["recommended_order_qty"].median())

    top20 = (
        out_df.sort_values("recommended_order_qty", ascending=False)
        .head(20)[["plu_code", "product_name", "product_category", "recommended_order_qty"]]
    )

    lines: List[str] = []
    lines.append("Order Recommendation Monthly V2 Final Report")
    lines.append(f"input_csv: {INPUT_CSV.as_posix()}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append(f"row_count: {len(out_df)}")
    lines.append(f"predict_date_min: {out_df['predict_date'].min()}")
    lines.append(f"predict_date_max: {out_df['predict_date'].max()}")
    lines.append(f"recommended_order_qty_positive_count: {int((out_df['recommended_order_qty'] > 0).sum())}")
    lines.append(f"recommended_order_qty_zero_count: {int((out_df['recommended_order_qty'] == 0).sum())}")
    lines.append(f"recommended_order_qty_sum: {int(out_df['recommended_order_qty'].sum())}")
    lines.append(f"recommended_order_qty_min_positive: {qty_min}")
    lines.append(f"recommended_order_qty_max_positive: {qty_max}")
    lines.append(f"recommended_order_qty_mean_positive: {qty_mean}")
    lines.append(f"recommended_order_qty_median_positive: {qty_median}")
    lines.append("")
    lines.append("[Top 20 recommended order products]")
    if top20.empty:
        lines.append("- None")
    else:
        for _, r in top20.iterrows():
            lines.append(
                f"- plu_code={r['plu_code']}, product_name={r['product_name']}, "
                f"product_category={r['product_category']}, recommended_order_qty={int(r['recommended_order_qty'])}"
            )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved recommendation csv: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Rows: {len(out_df)}")


if __name__ == "__main__":
    main()
