# Model API Spec (RandomForest Fast)

## 1. Model File
- Artifact: `random_forest_fast_model.pkl`
- Recommended repo path: `models/random_forest_fast_model.pkl`
- Runtime env option: `MODEL_PATH=./models/random_forest_fast_model.pkl`
- Type: `RandomForestRegressor` bundle (`model`, `feature_cols`, `categorical_cols`, `label_maps`)

## 2. Feature Schema
| feature | type | description |
|---|---|---|
| `plu_code` | `string` | 상품 PLU 코드 (원본 문자열, 서버에서 LabelEncoding 매핑 적용) |
| `product_category` | `string` | 상품 카테고리 (원본 문자열, 서버에서 LabelEncoding 매핑 적용) |
| `sales_qty` | `number` | 기준일 실제 판매수량 |
| `purchase_qty` | `number` | 기준일 매입수량 |
| `is_start_semester` | `number` | 개강일 여부 (0/1) |
| `is_end_semester` | `number` | 종강일 여부 (0/1) |
| `is_exam` | `number` | 시험기간 여부 (0/1) |
| `is_vacation` | `number` | 방학 여부 (0/1) |
| `is_festival` | `number` | 축제 여부 (0/1) |
| `is_holiday_or_no_class` | `number` | 휴강/공휴일/휴업 여부 (0/1) |
| `class_count` | `number` | 해당 요일 전체 수업량 지표 |
| `monday_class_count` | `number` | 월요일 수업 수 |
| `tuesday_class_count` | `number` | 화요일 수업 수 |
| `wednesday_class_count` | `number` | 수요일 수업 수 |
| `thursday_class_count` | `number` | 목요일 수업 수 |
| `friday_class_count` | `number` | 금요일 수업 수 |
| `year` | `number` | 기준일 연도 |
| `month` | `number` | 기준일 월 |
| `day` | `number` | 기준일 일 |
| `weekday` | `number` | 요일 인덱스 (월=0, ..., 일=6) |
| `is_weekend` | `number` | 주말 여부 (0/1) |
| `sales_lag_1` | `number` | 동일 상품 1일 전 판매량 |
| `sales_lag_7` | `number` | 동일 상품 7일 전 판매량 |
| `rolling_mean_7` | `number` | 동일 상품 최근 7일 이동평균 (현재일 제외) |
| `rolling_mean_14` | `number` | 동일 상품 최근 14일 이동평균 (현재일 제외) |
| `rolling_mean_28` | `number` | 동일 상품 최근 28일 이동평균 (현재일 제외) |

## 3. Preprocessing Rules
- 입력 feature는 학습 시 사용 순서와 동일한 `feature_cols` 순서로 구성해야 합니다.
- 범주형 컬럼(`plu_code`, `product_category`)은 **LabelEncoding**을 사용합니다.
- 학습 시점에 없는 신규 범주값은 `-1`로 매핑합니다.
- 수치형 컬럼 결측/비정상값은 `0`으로 대체합니다.
- 예측값이 음수면 최종 응답에서 `0`으로 보정합니다.

## 4. Categorical Encoding Info
- `plu_code` classes: `1038`
- `product_category` classes: `12`

## 5. Sample Request JSON
```json
{
  "base_date": "2026-02-01",
  "items": [
    {
      "plu_code": "8801056040925.0",
      "product_name": "롯데)칠성사이다캔355ml",
      "product_category": "음료",
      "features": {
        "plu_code": "8801056040925.0",
        "product_category": "음료",
        "sales_qty": 5.0,
        "purchase_qty": 5.0,
        "is_start_semester": 0,
        "is_end_semester": 0,
        "is_exam": 0,
        "is_vacation": 0,
        "is_festival": 0,
        "is_holiday_or_no_class": 0,
        "class_count": 5.0,
        "monday_class_count": 5.0,
        "tuesday_class_count": 5.0,
        "wednesday_class_count": 5.0,
        "thursday_class_count": 5.0,
        "friday_class_count": 5.0,
        "year": 2026,
        "month": 2,
        "day": 2,
        "weekday": 0,
        "is_weekend": 0,
        "sales_lag_1": 5.0,
        "sales_lag_7": 5.0,
        "rolling_mean_7": 5.0,
        "rolling_mean_14": 5.0,
        "rolling_mean_28": 5.0
      }
    }
  ],
  "safety_factor": 1.2
}
```

## 6. Sample Response JSON
```json
{
  "base_date": "2026-02-01",
  "predict_date": "2026-02-02",
  "results": [
    {
      "plu_code": "8801056040925.0",
      "product_name": "롯데)칠성사이다캔355ml",
      "product_category": "음료",
      "predicted_sales_qty": 18.42,
      "recommended_order_qty": 23
    }
  ]
}
```

## 7. Prediction Flow
1. 입력 수신: `base_date`, 상품 메타정보, feature 값
2. feature 생성/정렬: 학습과 동일한 `feature_cols` 기준으로 입력 벡터 구성
3. 범주형 인코딩: `label_maps`로 LabelEncoding 적용(미등록 값은 `-1`)
4. 모델 예측: `model.predict(X)`로 `predicted_sales_qty` 계산
5. 발주 추천 계산: `recommended_order_qty = ceil(predicted_sales_qty * safety_factor)`
6. 음수 보정: `predicted_sales_qty <= 0`이면 추천 발주량 `0`

## 8. Order Recommendation Formula
- `recommended_order_qty = ceil(predicted_sales_qty * safety_factor)`
- 기본 `safety_factor = 1.2`
- `predicted_sales_qty <= 0` 인 경우 `recommended_order_qty = 0`
