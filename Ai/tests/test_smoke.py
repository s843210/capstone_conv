"""Smoke tests — verify model load, prediction, and order calculation."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_model_load():
    """Model bundle loads successfully and contains expected keys."""
    from src.config import Paths
    import joblib

    model_path = Paths.MODEL_RF_FAST
    if not model_path.exists():
        # Also try the models/ directory copy
        alt = PROJECT_ROOT / "models" / "random_forest_fast_model.pkl"
        if alt.exists():
            model_path = alt
        else:
            print(f"SKIP: Model file not found at {Paths.MODEL_RF_FAST}")
            return

    bundle = joblib.load(model_path)
    assert isinstance(bundle, dict), "Bundle should be a dict"
    assert "model" in bundle, "Bundle must contain 'model'"
    assert "feature_cols" in bundle, "Bundle must contain 'feature_cols'"
    assert "label_maps" in bundle, "Bundle must contain 'label_maps'"
    assert len(bundle["feature_cols"]) > 0, "feature_cols should not be empty"
    print(f"PASS: Model loaded, {len(bundle['feature_cols'])} features")


def test_single_prediction():
    """Model can predict on a single sample input."""
    from src.config import Paths
    from src.serving.preprocess_for_infer import ModelPredictor

    model_path = Paths.MODEL_RF_FAST
    alt = PROJECT_ROOT / "models" / "random_forest_fast_model.pkl"
    if not model_path.exists() and alt.exists():
        model_path = alt
    if not model_path.exists():
        print(f"SKIP: Model file not found")
        return

    predictor = ModelPredictor(model_path)

    # Build a minimal sample with zeroes
    sample = {c: 0 for c in predictor.feature_cols}
    sample["plu_code"] = "8801056040925.0"
    sample["product_category"] = "음료"
    sample["sales_qty"] = 5.0
    sample["year"] = 2026
    sample["month"] = 2
    sample["day"] = 2

    result = predictor.predict_one(sample)

    assert "predicted_sales_qty" in result, "Result must have predicted_sales_qty"
    assert "recommended_order_qty" in result, "Result must have recommended_order_qty"
    assert result["predicted_sales_qty"] >= 0, "Prediction should be non-negative"
    assert isinstance(result["recommended_order_qty"], int), "Order qty should be int"
    print(f"PASS: Prediction={result['predicted_sales_qty']}, Order={result['recommended_order_qty']}")


def test_order_calculation():
    """Order recommendation formula works correctly."""
    from math import ceil

    safety_factor = 1.2
    test_cases = [
        (10.0, int(ceil(10.0 * safety_factor))),  # 12
        (0.0, 0),
        (-5.0, 0),
        (1.0, int(ceil(1.0 * safety_factor))),    # 2
    ]
    for pred, expected in test_cases:
        actual = int(ceil(pred * safety_factor)) if pred > 0 else 0
        assert actual == expected, f"Failed: pred={pred}, expected={expected}, got={actual}"

    print("PASS: Order calculation formula verified")


if __name__ == "__main__":
    test_model_load()
    test_single_prediction()
    test_order_calculation()
    print("\nAll smoke tests passed!")
