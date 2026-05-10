# Final Model API Spec (RandomForest + Binary Weather)

## 1. Final Model File
- Path: `outputs/models/random_forest_weather_binary_model.pkl`
- Bundle keys: `model`, `feature_cols`, `categorical_cols`, `label_maps`

## 2. Final Performance
- MAE: 12.8477
- RMSE: 24.1966
- R2: 0.6417

## 3. Improvement vs Existing RF-fast
- Existing RF-fast MAE: 14.3009 -> Final MAE: 12.8477
- Binary weather features (`is_rainy`, `is_hot`, `is_cold`) were added, and performance improved.

## 4. Model Input Features (from `feature_cols`)
| feature | type | description |
|---|---|---|
| `plu_code` | `string` | Product PLU code (string, label-encoded at inference). |
| `product_category` | `string` | Product category (string, label-encoded at inference). |
| `sales_qty` | `number` | Current observed sales quantity. |
| `purchase_qty` | `number` | Current observed purchase quantity. |
| `is_start_semester` | `number` | Start-of-semester flag (0/1). |
| `is_end_semester` | `number` | End-of-semester flag (0/1). |
| `is_exam` | `number` | Exam period flag (0/1). |
| `is_vacation` | `number` | Vacation period flag (0/1). |
| `is_festival` | `number` | Festival/event flag (0/1). |
| `is_holiday_or_no_class` | `number` | Holiday or no-class flag (0/1). |
| `class_count` | `number` | Class count for the date weekday. |
| `monday_class_count` | `number` | Monday class count. |
| `tuesday_class_count` | `number` | Tuesday class count. |
| `wednesday_class_count` | `number` | Wednesday class count. |
| `thursday_class_count` | `number` | Thursday class count. |
| `friday_class_count` | `number` | Friday class count. |
| `is_rainy` | `number` | Binary weather feature: 1 if rainfall > 0 else 0. |
| `is_hot` | `number` | Binary weather feature: 1 if avg_temp >= 27 else 0. |
| `is_cold` | `number` | Binary weather feature: 1 if avg_temp <= 5 else 0. |
| `year` | `number` | Year extracted from date. |
| `month` | `number` | Month extracted from date. |
| `day` | `number` | Day extracted from date. |
| `weekday` | `number` | Weekday index (Mon=0 ... Sun=6). |
| `is_weekend` | `number` | Weekend flag (0/1). |
| `sales_lag_1` | `number` | Previous sales quantity for same plu_code. |
| `sales_lag_7` | `number` | Sales quantity 7 steps before for same plu_code. |
| `rolling_mean_7` | `number` | Rolling mean over previous 7 points (after shift(1)). |
| `rolling_mean_14` | `number` | Rolling mean over previous 14 points (after shift(1)). |
| `rolling_mean_28` | `number` | Rolling mean over previous 28 points (after shift(1)). |

## 5. Categorical Encoding
- `plu_code`, `product_category` are LabelEncoded.
- Use `label_maps` inside model bundle for consistent encoding.
- Unknown category values should map to `-1`.
- `plu_code` classes in label map: 1038
- `product_category` classes in label map: 12

## 6. Binary Weather Features
- `is_rainy`: rain status flag (1 if rainy, else 0)
- `is_hot`: hot day flag (1 if hot, else 0)
- `is_cold`: cold day flag (1 if cold, else 0)

## 7. Weather Inputs Needed from Spring Server
- Provide `rainfall` directly, or provide `is_rainy` directly.
- From `avg_temp`, server can derive `is_hot` and `is_cold`.
- Derivation rules:
  - `is_rainy = rainfall > 0`
  - `is_hot = avg_temp >= 27`
  - `is_cold = avg_temp <= 5`

## 8. Sample Request JSON
```json
{
  "base_date": "2025-05-29",
  "weather_input": {
    "rainfall": 1.2,
    "avg_temp": 28.1,
    "derived_binary": {
      "is_rainy": 1,
      "is_hot": 1,
      "is_cold": 0
    }
  },
  "items": [
    {
      "plu_code": "1001258817890.0",
      "product_name": "sample_product",
      "product_category": "sample_category",
      "features": {
        "plu_code": "1001258817890.0",
        "product_category": "캔디/초콜릿",
        "sales_qty": 4.0,
        "purchase_qty": 0.0,
        "is_start_semester": 0.0,
        "is_end_semester": 0.0,
        "is_exam": 0.0,
        "is_vacation": 0.0,
        "is_festival": 0.0,
        "is_holiday_or_no_class": 0.0,
        "class_count": 87.0,
        "monday_class_count": 372.0,
        "tuesday_class_count": 369.0,
        "wednesday_class_count": 144.0,
        "thursday_class_count": 87.0,
        "friday_class_count": 75.0,
        "is_rainy": 0.0,
        "is_hot": 0.0,
        "is_cold": 0.0,
        "year": 2025.0,
        "month": 5.0,
        "day": 29.0,
        "weekday": 3.0,
        "is_weekend": 0.0,
        "sales_lag_1": 10.0,
        "sales_lag_7": 2.0,
        "rolling_mean_7": 3.857142857142857,
        "rolling_mean_14": 13.714285714285714,
        "rolling_mean_28": 8.714285714285714
      }
    }
  ],
  "safety_factor": 1.2
}
```

## 9. Sample Response JSON
```json
{
  "base_date": "2025-05-29",
  "predict_date": "2025-05-30",
  "results": [
    {
      "plu_code": "1001258817890.0",
      "product_name": "sample_product",
      "product_category": "sample_category",
      "predicted_sales_qty": 18.42,
      "recommended_order_qty": 23
    }
  ]
}
```

## 10. Order Recommendation Formula
- `recommended_order_qty = ceil(predicted_sales_qty * 1.2)`

## 11. Final Output File Paths
- Prediction output: `outputs/reports/tomorrow_sales_prediction_final.csv`
- Order recommendation output: `outputs/reports/order_recommendation_final.csv`