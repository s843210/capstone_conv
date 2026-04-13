# RandomForest 설계 계획 v3 (17:00 추론, 18:00 발주, D+1 예측)

## Summary
- 목표: `ms_sales_...features.csv`(확장 19컬럼)를 기반으로 상품별 **내일 판매량(D+1)** 예측 모델을 구축하고, 발주추천까지 연결한다.
- 운영 시점: 매일 **17:00 추론**, **18:00 발주**.
- 핵심 원칙:
  - 정답(y)은 `target_sales` 하나
  - `sales`/`target_sales`는 모델 입력(X)에서 제외
  - `safety_stock`은 모델 입력이 아니라 발주 후처리에만 사용

## Implementation Changes
1. 학습 테이블 생성(Feature -> Supervised)
- 입력 원본: `ms_sales_YYYY_MM_DD_to_YYYY_MM_DD_features.csv`
- 정렬 키: `plu_code`, `date` 오름차순
- 정답 생성:
  - `target_date = date + 1일`
  - `target_sales = same plu_code의 다음날 sales (shift -1)`
- 학습 제외:
  - `target_sales` 없는 마지막 날짜 행
  - 필요 시 `match_type != exact` 행(기본은 exact-only 유지)
- 최종 학습용 컬럼:
  - 식별자: `date, target_date, plu_code, product_name`
  - X 후보: `lag_1, lag_3, lag_7, rolling_7_mean, rolling_7_std, day_of_week, month, is_holiday, academic_event, building_headcount, category_l, category_m`
  - y: `target_sales`

2. 모델 설계(RandomForest)
- 모델: `RandomForestRegressor`
- 범주형 처리: `category_l`, `category_m` 원-핫 인코딩
- 기본 하이퍼파라미터(초기값 고정):
  - `n_estimators=500`
  - `max_depth=16`
  - `min_samples_split=5`
  - `min_samples_leaf=2`
  - `max_features='sqrt'`
  - `n_jobs=-1`
  - `random_state=42`
- 베이스라인 비교:
  - `naive_pred = lag_1`
  - RF가 베이스라인보다 개선되는지 필수 확인

3. 학습/평가 프로토콜
- 학습 데이터: 현재 확보된 2024-04-01 ~ 2024-05-31
- 평가 데이터: 2025-05-01 ~ 2025-05-31
- 평가용 변환 입력 권장: 최소 2025-04-24 ~ 2025-05-31(7일 워밍업)
- 평가 지표:
  - 1순위 `WAPE`
  - 2순위 `MAE`
  - 보조 `Bias(예측-실측 평균)`
- 리포트 단위:
  - 전체
  - `category_m`별

4. 운영 추론/발주 계산/API
- D일 17:00에 X 생성 후 `target_date = D+1` 예측
- 예측값 보정: `predicted_sales = max(0, round(pred))`
- 발주량:
  - `recommended_order = max(0, ceil(predicted_sales + safety_stock - current_stock))`
- Spring 전송 계약(현행 유지):
  - `POST /api/ai/predictions`
  - `targetDate = D+1`
  - `categories[].products[].{pluCode, predictedSales, recommendedOrder, confidenceScore}`
  - `categories[].totalRecommendedOrder`, `categories[].aiMessage`

## Test Plan
1. 타깃 정렬 검증
- 샘플 PLU 20개에서 `target_sales == next day sales` 확인

2. 누수 검증
- X에서 `sales`, `target_sales`, `safety_stock`, 식별자(`plu_code/date/product_name`) 제거 확인

3. 데이터 품질 검증
- 학습/평가셋 모두 날짜 역전/중복 키(`target_date+plu_code`) 확인
- lag/rolling 값 타입 및 범위 확인

4. 성능/운영 검증
- RF vs naive(`lag_1`) 지표 비교
- 추천발주 음수 0건 확인
- API 샘플 payload 저장 성공 및 `savedCount` 확인

## Assumptions
- 단일 매장 운영(`store_id` 미사용)
- `is_stockout`은 데이터 부재로 v1 제외
- 외생변수는 현행 기본값(`academic_event=0`, `building_headcount=0`)으로 시작
- `fuzzy_threshold=1.0`(exact-only) 운영 유지
