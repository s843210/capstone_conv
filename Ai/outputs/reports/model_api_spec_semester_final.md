# Final Model API Spec (Semester Binary)

## 1. Final Model
- Model path: `outputs/models/random_forest_semester_binary_model.pkl`
- Model type: `RandomForestRegressor`
- Bundle keys: `model`, `feature_cols`, `categorical_cols`, `label_maps`

## 2. Final Performance
- MAE: 13.024
- RMSE: 24.7452
- R2: 0.6253

## 3. Input Features
### feature_cols
| feature | type | description |
|---|---|---|
| `plu_code` | `string` | Product PLU code (string -> label encoded) |
| `product_category` | `string` | Product category (string -> label encoded) |
| `sales_qty` | `number` | Current observed sales quantity |
| `purchase_qty` | `number` | Current observed purchase quantity |
| `class_count` | `number` | Class count for current weekday |
| `monday_class_count` | `number` | Monday class count |
| `tuesday_class_count` | `number` | Tuesday class count |
| `wednesday_class_count` | `number` | Wednesday class count |
| `thursday_class_count` | `number` | Thursday class count |
| `friday_class_count` | `number` | Friday class count |
| `is_rainy` | `number` | 1 if rainfall > 0 else 0 |
| `is_hot` | `number` | 1 if avg_temp >= 27 else 0 |
| `is_cold` | `number` | 1 if avg_temp <= 5 else 0 |
| `is_semester` | `number` | 1 when not vacation, 0 when vacation |
| `year` | `number` | Year extracted from date |
| `month` | `number` | Month extracted from date |
| `day` | `number` | Day extracted from date |
| `weekday` | `number` | Weekday index (Mon=0 ... Sun=6) |
| `is_weekend` | `number` | Weekend flag |
| `sales_lag_1` | `number` | Lag-1 sales of same plu_code |
| `sales_lag_7` | `number` | Lag-7 sales of same plu_code |
| `rolling_mean_7` | `number` | Rolling mean over previous 7 points after shift(1) |
| `rolling_mean_14` | `number` | Rolling mean over previous 14 points after shift(1) |
| `rolling_mean_28` | `number` | Rolling mean over previous 28 points after shift(1) |

### categorical_cols
- `plu_code`
- `product_category`

## 4. Label Encoding (label_maps)
- `plu_code` and `product_category` must be encoded using `label_maps` from model bundle.
- Unknown values should be mapped to `-1`.
- `plu_code` class count: 1038
- `product_category` class count: 12

## 5. Rule Features
### is_semester
- Rule: `is_vacation == 1` -> `is_semester = 0`, otherwise `is_semester = 1`
### binary weather
- `is_rainy = rainfall > 0`
- `is_hot = avg_temp >= 27`
- `is_cold = avg_temp <= 5`

## 6. Order Recommendation Formula
- `recommended_order_qty = ceil(predicted_sales_qty * 1.2)`
- if `predicted_sales_qty <= 0`, then `recommended_order_qty = 0`

## 7. Sample Request JSON
```json
{
  "base_date": "2025-05-29",
  "weather_input": {
    "rainfall": 0.5,
    "avg_temp": 22.0,
    "derived_binary": {
      "is_rainy": 1,
      "is_hot": 0,
      "is_cold": 0
    }
  },
  "academic_input": {
    "is_vacation": 0,
    "derived_is_semester": 1
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
        "class_count": 87.0,
        "monday_class_count": 372.0,
        "tuesday_class_count": 369.0,
        "wednesday_class_count": 144.0,
        "thursday_class_count": 87.0,
        "friday_class_count": 75.0,
        "is_rainy": 0.0,
        "is_hot": 0.0,
        "is_cold": 0.0,
        "is_semester": 1.0,
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

## 8. Sample Response JSON
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

## 9. FastAPI Handoff Notes
1. Load model bundle once at app startup.
2. Build runtime features in exact `feature_cols` order.
3. Apply `label_maps` to categorical columns; unknown -> `-1`.
4. Cast numeric columns to float/int and fill missing with `0`.
5. Run `model.predict`, clip negatives to `0`, then compute order recommendation.
6. Persist prediction and recommendation outputs to report files if needed.