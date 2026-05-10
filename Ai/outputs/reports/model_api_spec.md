# Model API Spec (RandomForest + Binary Weather)

## 1. Model File
- Path: `outputs\models\random_forest_weather_binary_model.pkl`
- Bundle keys: `model`, `feature_cols`, `categorical_cols`, `label_maps`

## 2. Input Features
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

## 3. Categorical Encoding
- `plu_code`, `product_category` are LabelEncoded.
- Use `label_maps` inside model bundle for consistent encoding.
- Unknown category values should map to `-1`.
- `plu_code` classes: 993
- `product_category` classes: 12

## 4. Binary Weather Features
- `is_rainy`: 1 if rainfall > 0 else 0
- `is_hot`: 1 if avg_temp >= 27 else 0
- `is_cold`: 1 if avg_temp <= 5 else 0

## 5. Order Recommendation Formula
- `recommended_order_qty = ceil(predicted_sales_qty * 1.2)`