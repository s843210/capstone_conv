# 캠퍼스 편의점 수요예측 프로젝트

## 1. 프로젝트 개요
본 프로젝트는 캠퍼스 편의점 판매 데이터를 기반으로 **상품별 다음날 판매량(`target_sales`)**을 예측하고, 예측값 기반으로 **발주 추천 수량**을 생성하는 파이프라인입니다.

데이터는 판매데이터, 상품 마스터, 학사일정, 시간표를 결합해 모델 학습용 피처를 만들고, Baseline/RandomForest/LightGBM 성능을 비교해 최종 모델을 선정했습니다.

---

## 2. 폴더 구조
```text
caps/
├─ data/
│  ├─ raw/
│  │  ├─ sales/
│  │  ├─ product/
│  │  ├─ calendar/
│  │  └─ timetable/
│  └─ processed/
│     ├─ daily_sales_raw_v2.csv
│     ├─ product_master.csv
│     ├─ product_master_representative.csv
│     ├─ final_sales_dataset.csv
│     ├─ sales_with_calendar.csv
│     ├─ timetable_features.csv
│     ├─ sales_with_calendar_timetable.csv
│     └─ model_features.csv
├─ outputs/
│  ├─ models/
│  │  ├─ random_forest_fast_model.pkl
│  │  └─ lightgbm_model.pkl
│  └─ reports/
│     ├─ baseline_result.json
│     ├─ random_forest_fast_result.json
│     ├─ lightgbm_result.json
│     ├─ model_comparison.csv
│     ├─ best_model_summary.json
│     ├─ tomorrow_sales_prediction.csv
│     └─ order_recommendation.csv
├─ src/
│  ├─ 01_...py ~ 30_...py
│  └─ 28_compare_models.py
├─ requirements.txt
└─ README.md
```

---

## 3. 데이터 설명
- `sales`:
  - 일별 구조: `YYMMDD/MMDD카테고리.xlsx`
  - 월별 구조: `YYMM카테고리.xlsx`
- `product`:
  - 카테고리별 상품분류 기준표 (CSV 중심)
- `calendar`:
  - 학사일정(`date`, `event`)
- `timetable`:
  - 연도별 수업 시간표

---

## 4. 전처리 순서
1. 파일명 표준화 (`sales_YYYY_MM`, `product_master`, `academic_calendar_2026`, `timetable_*`)
2. 판매데이터 구조 탐색 및 실제 헤더 탐지 로직 확인
3. 전체 판매 파일 정제/병합 (`daily_sales_raw_v2.csv`)
4. 판매 병합 결과 검증 및 날짜 파싱 이슈 진단/수정
5. 상품 마스터 통합 (`product_master.csv`)
6. 상품명 매칭률 진단 및 대표 PLU 테이블 생성 (`product_master_representative.csv`)
7. 판매+상품 결합 (`daily_sales_with_product.csv`)
8. 학사일정 feature 생성 (`academic_calendar_features.csv`)
9. 판매+학사일정 결합 (`sales_with_calendar.csv`)
10. 시간표 feature 생성 (`timetable_features.csv`)
11. 판매+학사일정+시간표 결합 (`sales_with_calendar_timetable.csv`)
12. 모델 피처셋 생성 (`model_features.csv`)

---

## 5. 모델 학습 순서
1. **Baseline**
   - 예측값: `rolling_mean_7`
2. **RandomForest-fast**
   - `LabelEncoding(plu_code, product_category)`
   - `n_estimators=100`, `max_depth=20`, `min_samples_leaf=3`
3. **LightGBM**
   - `LabelEncoding(plu_code, product_category)`
   - `n_estimators=500`, `learning_rate=0.05`, `max_depth=-1`

---

## 6. 최종 선택 모델
- 선택 모델: **`RandomForestRegressor_fast`**
- 선택 기준:
  - MAE 최소 우선
  - 동률 시 RMSE 최소

---

## 7. 성능 비교 결과
`outputs/reports/model_comparison.csv` 기준:

- Baseline
  - MAE: `16.5875`
  - RMSE: `30.9979`
  - R2: `0.4120`
- RandomForest-fast
  - MAE: `14.3009`
  - RMSE: `26.2230`
  - R2: `0.5792`
- LightGBM
  - MAE: `24.4236`
  - RMSE: `33.9968`
  - R2: `0.2928`

---

## 8. 예측 결과 파일 설명
- 파일: `outputs/reports/tomorrow_sales_prediction.csv`
- 컬럼:
  - `base_date`: 예측 기준일
  - `predict_date`: 예측 대상일(기준일 + 1일)
  - `plu_code`
  - `product_name`
  - `product_category`
  - `predicted_sales_qty`: 모델 예측 판매량

---

## 9. 발주 추천 로직 설명
- 입력: `tomorrow_sales_prediction.csv`
- 로직:
  - `recommended_order_qty = ceil(predicted_sales_qty * safety_factor)`
  - `safety_factor = 1.2`
  - `predicted_sales_qty <= 0`이면 추천 발주량 `0`
- 출력:
  - `outputs/reports/order_recommendation.csv`
  - `outputs/reports/order_recommendation_summary.txt`

---

## 10. 실행 방법
### 1) 환경 준비
```bash
pip install -r requirements.txt
```

### 2) 전체 파이프라인(핵심 단계)
```bash
py src/17_build_final_sales_dataset.py
py src/20_merge_sales_with_calendar.py
py src/22_build_timetable_features.py
py src/23_merge_sales_with_timetable.py
py src/24_build_model_features.py
py src/25_train_baseline.py
py src/26_train_random_forest_fast.py
py src/27_train_lightgbm.py
py src/28_compare_models.py
py src/29_make_tomorrow_prediction.py
py src/30_make_order_recommendation.py
```

### 3) 주요 결과 확인
- 모델 비교: `outputs/reports/model_comparison.csv`, `best_model_summary.json`
- 내일 예측: `outputs/reports/tomorrow_sales_prediction.csv`
- 발주 추천: `outputs/reports/order_recommendation.csv`
