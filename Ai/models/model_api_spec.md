# Monthly V2 AI Feature Contract

This is the source-of-truth contract for the MVP Spring <-> FastAPI integration.
The first FastAPI version wraps the existing CSV-based `monthly_v2` pipeline. A later version may replace the CSV input builder with DB queries, but the request/response shape below must stay stable.

## 1. Model And Pipeline

- Model name: `random_forest_monthly_v2`
- Model path: `Ai/outputs/models/random_forest_monthly_v2_model.pkl`
- Feature CSV: `Ai/data/processed/model_features_monthly_v2.csv`
- Prediction CSV: `Ai/outputs/reports/tomorrow_sales_prediction_monthly_v2_final.csv`
- Recommendation CSV: `Ai/outputs/reports/order_recommendation_monthly_v2_final.csv`
- Predict command used by the CSV wrapper: `python Ai/run_pipeline.py --step predict`
- Train command used by the CSV wrapper: `python Ai/run_pipeline.py --step train`

## 2. MVP Recommendation Target Filter

FastAPI/Spring must apply the same candidate policy before saving dashboard recommendations.

- Include active products only: `product.is_active = true`.
- Exclude uncategorized products: `product.category != '미분류'`.
- Require sales history: at least one `daily_sales` row exists for the PLU.
- Require inventory presence: product exists from the current-stock upload flow, with a usable `product.current_stock`.
- Dashboard default view should show products with `recommended_order > 0`.
- `미분류` products stay visible in inventory 조회, but are not part of MVP AI recommendations.

## 3. Monthly V2 Feature Columns

The model feature builder produces the following columns. `target_sales` is the training label and must not be sent as an inference feature.

| column | role | type |
|---|---|---|
| `date` | base date | date |
| `plu_code` | feature/key | string |
| `product_name` | metadata | string |
| `product_category` | feature/category | string |
| `sales_qty` | feature | number |
| `class_count` | feature | number |
| `monday_class_count` | feature | number |
| `tuesday_class_count` | feature | number |
| `wednesday_class_count` | feature | number |
| `thursday_class_count` | feature | number |
| `friday_class_count` | feature | number |
| `year` | feature | integer |
| `month` | feature | integer |
| `day` | feature | integer |
| `weekday` | feature | integer, Monday=0 |
| `is_weekend` | feature | 0/1 |
| `sales_lag_1` | feature | number |
| `sales_lag_7` | feature | number |
| `rolling_mean_7` | feature | number |
| `rolling_mean_14` | feature | number |
| `rolling_mean_28` | feature | number |
| `target_sales` | train label only | number |
| `is_rainy` | feature | 0/1 |
| `is_hot` | feature | 0/1 |
| `is_cold` | feature | 0/1 |
| `is_semester` | feature | 0/1 |

Inference features are all feature/key/category columns except `date`, `product_name`, and `target_sales`.

## 4. FastAPI Predict Endpoint

Endpoint:

```http
POST /ai/monthly-v2/predict
```

Request:

```json
{
  "target_date": "2026-04-24",
  "mode": "csv",
  "persist_to_spring": false,
  "recommendation_policy": {
    "exclude_uncategorized": true,
    "require_sales_history": true,
    "require_current_stock": true,
    "only_positive_recommendations": false
  }
}
```

Rules:

- `target_date` is required from Spring. If a local/manual call omits it, FastAPI may default to tomorrow in `Asia/Seoul`.
- `mode = "csv"` means use the existing CSV artifacts and monthly_v2 scripts.
- `persist_to_spring = true` means FastAPI may POST the mapped result to Spring `/api/ai/predictions`.
- The response must use one canonical `target_date`. If the legacy CSV contains multiple `predict_date` values, the wrapper must filter or normalize rows before returning/saving.

Response:

```json
{
  "run_id": "20260511-201500-monthly-v2-predict",
  "status": "SUCCESS",
  "model_name": "random_forest_monthly_v2",
  "target_date": "2026-04-24",
  "row_count": 586,
  "csv_outputs": {
    "prediction_csv": "Ai/outputs/reports/tomorrow_sales_prediction_monthly_v2_final.csv",
    "recommendation_csv": "Ai/outputs/reports/order_recommendation_monthly_v2_final.csv"
  },
  "results": [
    {
      "plu_code": "8801043015653",
      "product_name": "농심)육개장사발면",
      "product_category": "가공식품",
      "target_date": "2026-04-24",
      "predicted_sales": 27.1563,
      "recommended_order": 33,
      "confidence_score": null
    }
  ]
}
```

Canonical result row:

| field | required | type | note |
|---|---:|---|---|
| `plu_code` | yes | string | Product PLU used for Spring `product` lookup |
| `product_name` | yes | string | Display/debug metadata |
| `product_category` | yes | string | Must not be `미분류` for MVP recommendations |
| `target_date` | yes | date | Same value for every row in one run |
| `predicted_sales` | yes | number | Non-negative monthly_v2 prediction, keep decimals in FastAPI JSON |
| `recommended_order` | yes | integer | Final order recommendation |
| `confidence_score` | yes | number or null | `null` for monthly_v2 MVP until calibration is added |

## 5. CSV Output Contract

Prediction CSV:

```csv
base_date,predict_date,plu_code,product_name,product_category,predicted_sales_qty
```

Recommendation CSV:

```csv
base_date,predict_date,plu_code,product_name,product_category,predicted_sales_qty,recommended_order_qty
```

Mapping to canonical JSON:

| CSV column | JSON field |
|---|---|
| `predict_date` | `target_date` |
| `plu_code` | `plu_code` |
| `product_name` | `product_name` |
| `product_category` | `product_category` |
| `predicted_sales_qty` | `predicted_sales` |
| `recommended_order_qty` | `recommended_order` |

## 6. Recommendation Formula

The current monthly_v2 script uses:

```text
if predicted_sales <= 0:
    recommended_order = 0
else:
    recommended_order = ceil(predicted_sales * 1.2)
    if recommended_order < 2:
        recommended_order = 0
```

This formula is part of the MVP contract. Do not reimplement a different formula in Spring or the dashboard.

## 7. Spring Persistence Mapping

Spring already persists AI rows into `ai_prediction` through `/api/ai/predictions`.

FastAPI canonical rows map to Spring as:

| FastAPI field | Spring DTO / DB |
|---|---|
| `target_date` | `targetDate` / `ai_prediction.target_date` |
| `plu_code` | `pluCode` -> active `product.id` |
| `predicted_sales` | `predictedSales` as rounded integer for `ai_prediction.predicted_sales` |
| `recommended_order` | `recommendedOrder` / `ai_prediction.recommended_order` |
| `confidence_score` | `confidenceScore` / `ai_prediction.confidence_score` |
| `product_category` | grouping key for existing nested Spring DTO |

Until Spring adds a flat prediction ingestion endpoint, the Spring executor should group FastAPI rows by `product_category` and send the existing nested DTO:

```json
{
  "targetDate": "2026-04-24",
  "categories": [
    {
      "categoryName": "가공식품",
      "totalRecommendedOrder": 33,
      "aiMessage": "monthly_v2 recommendation",
      "products": [
        {
          "pluCode": "8801043015653",
          "predictedSales": 27,
          "recommendedOrder": 33,
          "confidenceScore": null
        }
      ]
    }
  ]
}
```

## 8. FastAPI Train Endpoint

Endpoint:

```http
POST /ai/monthly-v2/train
```

Request:

```json
{
  "mode": "csv",
  "force": false
}
```

Response:

```json
{
  "run_id": "20260511-201500-monthly-v2-train",
  "status": "SUCCESS",
  "model_name": "random_forest_monthly_v2",
  "model_path": "Ai/outputs/models/random_forest_monthly_v2_model.pkl",
  "metrics": {
    "mae": 0.7728685329953058,
    "rmse": 3.396173079091971,
    "r2": 0.01631106367124202
  }
}
```

## 9. DB-Based Phase Compatibility

When FastAPI changes from CSV input to DB input:

- Keep the same `/ai/monthly-v2/predict` response shape.
- Build the same feature columns from `daily_sales`, `daily_context`, `product`, and `inventory_snapshot`.
- Keep the same recommendation target filter and recommendation formula.
- Keep `confidence_score = null` unless a calibrated confidence method is implemented.
