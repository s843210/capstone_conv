# [PR] RandomForest 수요예측/발주추천 v1 설계 계획서

## Summary
- 목적: `판매현황 -> feature 생성 -> RandomForest 학습/추론 -> 발주추천 -> Spring 저장`을 v1으로 고정합니다.
- 기준 데이터: 현재 확보된 `2024-04-01 ~ 2024-05-31` 2개월 데이터 사용.
- 핵심 원칙: `target_sales`는 학습용 정답(y), `safety_stock`은 예측 입력이 아니라 발주 후처리에 사용.
- 현재 백엔드 계약(`/api/ai/predictions`)은 유지하고, FastAPI 출력만 정확히 맞춥니다.

## Implementation Changes
### 1) 학습 데이터셋 스펙 고정
- 입력 feature 컬럼(X): `lag_1, lag_3, lag_7, rolling_7_mean, rolling_7_std, day_of_week, month, is_holiday, academic_event, building_headcount, category`
- 식별/메타 컬럼: `date, plu_code`
- 제외 컬럼: `is_stockout`(현재 수집 불가), `price`(민감정보), `safety_stock`(후처리 전용)
- 타깃(y): `target_sales = plu_code별 다음날 sales(shift -1)`
- 누락 처리: lag/rolling 누락은 0, `target_sales`가 없는 마지막 일자 행은 학습 제외
- 단일 매장 기준으로 `store_id`는 v1에서 사용하지 않음

### 2) RandomForest 학습 설계
- 모델: `RandomForestRegressor`
- 인코딩: `category` 원-핫, 나머지 수치형 그대로
- 기본 하이퍼파라미터:
`n_estimators=500, max_depth=16, min_samples_split=5, min_samples_leaf=2, max_features='sqrt', n_jobs=-1, random_state=42`
- 데이터 분할: 시간순 Out-of-Time 분할
- 규칙: 마지막 14일 검증, 그 이전 학습
- 평가 지표: `WAPE`(주지표), `MAE`(보조), `Bias`(과대/과소 확인)
- 산출물: `model.pkl`, `feature_columns.json`, `category_encoder.pkl`, `metrics.json`

### 3) 추론 및 발주추천 로직
- 입력: 당일 기준 feature + 현재 재고(`current_stock`)
- 예측: `predicted_sales = max(0, round(model.predict(X)))`
- 안전재고 계산: 기존 규칙 유지
- 권장발주 계산식:
`recommended_order = max(0, ceil(predicted_sales + safety_stock - current_stock))`
- 카테고리 합계:
`totalRecommendedOrder = category별 recommended_order 합`
- 신뢰도 점수(`confidenceScore`): 트리별 예측 분산 기반 0~1 정규화
- `aiMessage` 생성: 카테고리별 템플릿 규칙
- 조건: 수요급증, 재고부족, 공휴일효과 중 해당 조건 문구 조합
- 기본: 조건 미충족 시 “평시 수요 기반 권장 발주”

### 4) FastAPI -> Spring API 계약 고정
- 엔드포인트: `POST /api/ai/predictions`
- 요청 스키마는 현재 백엔드 DTO와 동일하게 유지:
`targetDate`, `categories[].categoryName`, `categories[].totalRecommendedOrder`, `categories[].aiMessage`, `categories[].products[].pluCode`, `predictedSales`, `recommendedOrder`, `confidenceScore`
- 타입 고정:
`pluCode=string`, `predictedSales/recommendedOrder=int`, `confidenceScore=double`
- 매칭 기준: Spring은 `pluCode`로 active 상품 매핑, 미존재 상품은 skip(현행 유지)

## Test Plan
1. 데이터셋 생성 테스트  
- `target_sales`가 `shift(-1)`로 정확히 생성되는지 샘플 PLU 10개 수동 검증
- 누락/이상치 처리 후 컬럼 null 비율 0인지 확인

2. 누수 방지 테스트  
- 학습 feature에 `target_sales`, 당일 실제판매량 직접값, `safety_stock`이 포함되지 않는지 검증

3. 학습/검증 테스트  
- OOT 분할에서 WAPE/MAE/Bias 리포트 생성
- 카테고리별 성능 테이블(표본수 포함) 출력

4. 추론/후처리 테스트  
- `recommended_order` 음수 미발생 보장
- `current_stock` 변화 시 권장발주가 기대대로 반응하는지 케이스 테스트

5. API 계약 테스트  
- 샘플 payload 1건/대량 payload 1건으로 `/api/ai/predictions` 저장 성공 확인
- `savedCount`와 전송 상품 수 일치 여부 점검

## Assumptions / Defaults
- v1은 단일 매장 운영으로 `store_id` 미사용
- `is_stockout`은 데이터 부재로 제외
- 날씨 변수는 v1 제외, 필요 시 외생변수 CSV 조인으로 v2 확장
- 날짜 포맷은 `YYYY-MM-DD`, PLU는 문자열로 일관 처리
- feature 변환 시 매칭은 `fuzzy_threshold=1.0` 기본 사용

## PR Checklist
- [ ] `target_sales` 생성 파이프라인 추가
- [ ] RandomForest 학습 스크립트 및 아티팩트 저장 추가
- [ ] 추론 + 발주 후처리(`safety_stock` 적용) 추가
- [ ] FastAPI 응답을 Spring `/api/ai/predictions` 스키마로 고정
- [ ] OOT 평가 리포트(WAPE/MAE/Bias) 출력 추가
- [ ] E2E 테스트(변환 -> 학습 -> 추론 -> 저장) 통과
