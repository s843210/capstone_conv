# 팀 전달용 전체 설명서 (수요예측 + 발주추천)

## 1) 프로젝트 목표
- 상품별 **다음날 판매량(`target_sales`)** 예측
- 예측값 기반 **추천 발주 수량** 생성

---

## 2) 데이터 처리 흐름 요약
1. 판매데이터 정제/병합
2. 상품마스터 통합 및 상품명 매칭
3. 판매 + 상품정보 결합
4. 학사일정 feature 생성 및 결합
5. 시간표 feature 생성 및 결합
6. 모델 학습용 피처셋 생성 (`model_features.csv`)

핵심 학습 데이터:
- `data/processed/model_features.csv`

---

## 3) 모델 학습/평가 기준
- Train: `2024-04-02 ~ 2025-12-31`
- Test: `2026-01-01 이후`
- 평가 지표: MAE, RMSE, R2

---

## 4) 모델 성능 결과
### Baseline (rolling_mean_7)
- MAE: `16.5875`
- RMSE: `30.9979`
- R2: `0.4120`

### RandomForest-fast
- MAE: `14.3009`
- RMSE: `26.2230`
- R2: `0.5792`

### LightGBM
- MAE: `24.4236`
- RMSE: `33.9968`
- R2: `0.2928`

비교 결과 파일:
- `outputs/reports/model_comparison.csv`
- `outputs/reports/best_model_summary.json`

---

## 5) 최종 선택 모델
- 모델명: `RandomForestRegressor_fast`
- 모델 파일: `outputs/models/random_forest_fast_model.pkl`
- 선택 기준:
  1. MAE 최소
  2. 동률 시 RMSE 최소

---

## 6) FastAPI 연동 시 핵심 포인트
필수 전달 파일:
1. `random_forest_fast_model.pkl`
2. `model_api_spec.md`
3. `requirements.txt`

권장 추가 파일:
- `32_interactive_prediction_test.py`
- `FASTAPI_FILE_HANDOFF_CHECKLIST.md`
- `FASTAPI_HANDOFF_NOTE.txt`

전처리 필수 규칙:
- 입력 feature는 학습과 동일한 컬럼/순서 사용 (`feature_cols`)
- 범주형(`plu_code`, `product_category`)은 LabelEncoding 적용
- 학습에 없던 신규 범주값은 `-1` 처리
- 수치 결측은 `0` 처리
- 예측값 음수는 `0`으로 보정

---

## 7) 예측 결과 파일(`tomorrow_sales_prediction.csv`) 관련 중요 설명
이 파일은 **운영 확정본이 아니라 예시(샘플) 결과 파일**입니다.

이유:
- 상품별로 `base_date`가 서로 다를 수 있음
- 즉, 모든 상품이 동일 기준일에서 예측된 배치 결과가 아님

현재 파일 성격:
- 각 상품의 "가장 최신 데이터 1건"을 기준으로 다음날 예측
- 그래서 `base_date`, `predict_date`가 상품별로 달라질 수 있음

운영 배치에서는:
- 기준일을 하나로 고정(예: `2026-02-01`)
- 전체 상품을 같은 `predict_date`로 일괄 예측하는 방식이 필요

---

## 8) 발주 추천 로직
- 공식:
  - `recommended_order_qty = ceil(predicted_sales_qty * safety_factor)`
- 기본 `safety_factor = 1.2`
- `predicted_sales_qty <= 0`이면 추천 발주량은 `0`

산출물:
- `outputs/reports/order_recommendation.csv`
- `outputs/reports/order_recommendation_summary.txt`

---

## 9) 전달 시 권장 멘트 (복붙용)
> 모델은 `random_forest_fast_model.pkl` 기준으로 확정되었습니다.  
> `model_api_spec.md`에 입력/출력 스키마와 전처리 규칙이 정리되어 있습니다.  
> `tomorrow_sales_prediction.csv`는 포맷 확인용 샘플 결과이며, 운영 배치 결과가 아닙니다.  
> 운영 적용 시에는 기준일을 고정해 전체 상품을 같은 예측일로 일괄 추론해야 합니다.

