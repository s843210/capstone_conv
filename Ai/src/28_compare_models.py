from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE_DIR / "outputs" / "reports"

BASELINE_JSON = REPORT_DIR / "baseline_result.json"
RF_FAST_JSON = REPORT_DIR / "random_forest_fast_result.json"
LGBM_JSON = REPORT_DIR / "lightgbm_result.json"

OUT_COMPARISON_CSV = REPORT_DIR / "model_comparison.csv"
OUT_BEST_JSON = REPORT_DIR / "best_model_summary.json"

OUT_MAE_PNG = REPORT_DIR / "model_comparison_mae.png"
OUT_RMSE_PNG = REPORT_DIR / "model_comparison_rmse.png"
OUT_R2_PNG = REPORT_DIR / "model_comparison_r2.png"


def load_metrics(path: Path, model_name_fallback: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    metrics = obj.get("metrics_test", {})
    runtime = obj.get("runtime", {})
    return {
        "model_name": obj.get("model", model_name_fallback),
        "MAE": float(metrics.get("mae")),
        "RMSE": float(metrics.get("rmse")),
        "R2": float(metrics.get("r2")),
        "train_time_sec": float(runtime.get("train_seconds", 0.0)),
        "source_file": path.name,
    }


def save_bar_chart(df: pd.DataFrame, metric_col: str, out_path: Path, title: str) -> None:
    plt.figure(figsize=(8, 5))
    plt.bar(df["model_name"], df[metric_col])
    plt.title(title)
    plt.xlabel("Model")
    plt.ylabel(metric_col)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    rows = [
        load_metrics(BASELINE_JSON, "Baseline"),
        load_metrics(RF_FAST_JSON, "RandomForest-fast"),
        load_metrics(LGBM_JSON, "LightGBM"),
    ]
    comp_df = pd.DataFrame(rows)

    # 3) best model selection: lowest MAE, tie-breaker lowest RMSE
    best_row = comp_df.sort_values(["MAE", "RMSE"], ascending=[True, True]).iloc[0]

    # 5) save comparison table and best summary
    comp_df[["model_name", "MAE", "RMSE", "R2", "train_time_sec"]].to_csv(
        OUT_COMPARISON_CSV, index=False, encoding="utf-8-sig"
    )

    best_summary = {
        "selected_model": best_row["model_name"],
        "selection_rule": "lowest MAE, tie-breaker lowest RMSE",
        "metrics": {
            "MAE": float(best_row["MAE"]),
            "RMSE": float(best_row["RMSE"]),
            "R2": float(best_row["R2"]),
            "train_time_sec": float(best_row["train_time_sec"]),
        },
        "all_models": comp_df[
            ["model_name", "MAE", "RMSE", "R2", "train_time_sec", "source_file"]
        ].to_dict(orient="records"),
    }
    OUT_BEST_JSON.write_text(json.dumps(best_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6~7) charts
    save_bar_chart(comp_df, "MAE", OUT_MAE_PNG, "Model Comparison - MAE")
    save_bar_chart(comp_df, "RMSE", OUT_RMSE_PNG, "Model Comparison - RMSE")
    save_bar_chart(comp_df, "R2", OUT_R2_PNG, "Model Comparison - R2")

    print(f"Saved comparison csv: {OUT_COMPARISON_CSV}")
    print(f"Saved best model summary: {OUT_BEST_JSON}")
    print(f"Saved chart: {OUT_MAE_PNG}")
    print(f"Saved chart: {OUT_RMSE_PNG}")
    print(f"Saved chart: {OUT_R2_PNG}")
    print(f"Best model: {best_row['model_name']}")


if __name__ == "__main__":
    main()
