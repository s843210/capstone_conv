"""
RandomForest 판매량 예측 프로토타입 v4
- 플랜: PLAN_v4_optimized.md 기반
- 입력: ms_sales_2024_04_01_to_2024_05_31_features.csv (19컬럼, 23,689행)
- 목표: 상품별 D+1 판매량 예측 → 발주추천
"""

import warnings
warnings.filterwarnings("ignore")
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
from math import ceil
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error
import json
from datetime import timedelta

# ============================================================
# 0. 설정값 (Configuration)
# ============================================================
# 데이터 파일 경로
DATA_PATH = r"C:\Users\김민서\Desktop\ms_sales_2024_04_01_to_2024_05_31_features.csv"

# 시간 기반 분할 기준일 (이 날짜까지 Train, 이후 Test)
TRAIN_END_DATE = "2024-05-17"
TEST_START_DATE = "2024-05-18"
TEST_END_DATE = "2024-05-30"  # 5/31은 target_sales가 NaN이므로 제외

# 모델 입력(X)에 사용할 피처 목록 (12개)
FEATURE_COLS = [
    "lag_1", "lag_3", "lag_7",           # 시차 피처: 1일/3일/7일 전 판매량
    "rolling_7_mean", "rolling_7_std",   # 이동 통계: 7일 평균/표준편차
    "day_of_week",                       # 요일 (0=월 ~ 6=일)
    "month",                             # 월 (4 또는 5)
    "is_holiday",                        # 공휴일 여부 (0/1)
    "academic_event",                    # 학사 이벤트 여부 (0/1)
    "building_headcount",                # 건물 유동인구 (현재 기본값 0)
    "category_l",                        # 대분류 (LabelEncoded)
    "category_m",                        # 중분류 (LabelEncoded)
]

# 정답(y) 컬럼
TARGET_COL = "target_sales"

# 모델 입력에서 반드시 제외할 컬럼과 사유
EXCLUDED_COLS = {
    "sales": "정답 누수 위험 (target_sales의 원본)",
    "target_sales": "정답 그 자체",
    "safety_stock": "발주 후처리 전용, 예측에 무관",
    "category_s": "고유값 132개 → 과도한 차원",
    "match_type": "전량 exact → 정보 없음",
    "date": "식별자",
    "target_date": "식별자",
    "plu_code": "식별자",
    "product_name": "식별자",
}

# RandomForest 하이퍼파라미터
RF_PARAMS = {
    "n_estimators": 500,       # 트리 개수: 22K행 규모에서 안정적 앙상블
    "max_depth": 16,           # 최대 깊이: 12개 피처 대비 충분, 과적합 방지
    "min_samples_split": 5,    # 분할 최소 샘플: 소량 판매 노이즈 방지
    "min_samples_leaf": 2,     # 리프 최소 샘플: 일반화 확보
    "max_features": "sqrt",    # 피처 서브샘플: sqrt(12) ≈ 3~4개
    "n_jobs": -1,              # 전체 CPU 코어 사용
    "random_state": 42,        # 재현성 보장
}


# ============================================================
# 1. 데이터 로드 및 기본 검증 (Data Loading & Validation)
# ============================================================
print("=" * 70)
print("1단계: 데이터 로드 및 기본 검증")
print("=" * 70)

df = pd.read_csv(DATA_PATH)
print(f"  원본 데이터: {df.shape[0]:,}행 x {df.shape[1]}컬럼")
print(f"  기간: {df['date'].min()} ~ {df['date'].max()}")
print(f"  PLU 수: {df['plu_code'].nunique():,}개")
print(f"  결측치: {df.isnull().sum().sum()}건")

# match_type 전량 exact 확인
assert (df["match_type"] == "exact").all(), "match_type에 exact가 아닌 값 존재!"
print(f"  match_type: 전량 exact 확인 ✓")


# ============================================================
# 2. target_sales 생성 (Supervised Label Creation)
# ============================================================
print("\n" + "=" * 70)
print("2단계: target_sales 생성 (D+1 판매량)")
print("=" * 70)

# plu_code, date 기준 정렬 (shift(-1)이 올바르게 동작하도록)
df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)

# 동일 PLU 내에서 다음 날 판매량을 target으로 설정
# shift(-1): 현재 행에 "다음 행의 sales"를 가져옴
df["target_sales"] = df.groupby("plu_code")["sales"].shift(-1)

# target_date: 예측 대상 날짜 (date + 1일)
df["target_date"] = pd.to_datetime(df["date"]) + timedelta(days=1)
df["target_date"] = df["target_date"].dt.strftime("%Y-%m-%d")

# 각 PLU의 마지막 날짜는 target_sales가 NaN → 제거
rows_before = len(df)
df = df.dropna(subset=["target_sales"]).reset_index(drop=True)
df["target_sales"] = df["target_sales"].astype(int)

print(f"  NaN 제거: {rows_before - len(df):,}행 (각 PLU 마지막 날짜)")
print(f"  유효 행: {len(df):,}행")


# ============================================================
# 3. 타깃 정렬 검증 (Target Alignment Verification)
# ============================================================
print("\n" + "=" * 70)
print("3단계: 타깃 정렬 검증 (샘플 PLU 20개)")
print("=" * 70)

# 랜덤 PLU 20개 선택하여 target_sales가 실제 다음 날 sales와 일치하는지 검증
sample_plus = df["plu_code"].unique()[:20]
verification_errors = 0

for plu in sample_plus:
    plu_df = df[df["plu_code"] == plu].sort_values("date")
    for i in range(len(plu_df) - 1):
        current_row = plu_df.iloc[i]
        next_row = plu_df.iloc[i + 1]
        # 현재 행의 target_sales가 다음 행의 sales와 같아야 함
        if current_row["target_sales"] != next_row["sales"]:
            verification_errors += 1

if verification_errors == 0:
    print(f"  샘플 PLU 20개 검증 통과 ✓ (target_sales == next day sales)")
else:
    print(f"  ⚠ 검증 실패: {verification_errors}건 불일치")


# ============================================================
# 4. 범주형 인코딩 (Label Encoding)
# ============================================================
print("\n" + "=" * 70)
print("4단계: 범주형 인코딩 (LabelEncoder)")
print("=" * 70)

# RF는 트리 기반 → 원-핫 인코딩 불필요, LabelEncoder가 효율적
# category_l: 15 고유값, category_m: 49 고유값
le_cat_l = LabelEncoder()
le_cat_m = LabelEncoder()

df["category_l"] = le_cat_l.fit_transform(df["category_l"])
df["category_m"] = le_cat_m.fit_transform(df["category_m"])

print(f"  category_l: {len(le_cat_l.classes_)}개 클래스 → 0~{len(le_cat_l.classes_)-1}")
print(f"  category_m: {len(le_cat_m.classes_)}개 클래스 → 0~{len(le_cat_m.classes_)-1}")


# ============================================================
# 5. 시간 기반 학습/평가 분할 (Time-based Split)
# ============================================================
print("\n" + "=" * 70)
print("5단계: 시간 기반 학습/평가 분할")
print("=" * 70)

# 시간 순서 기반 분할: 미래 데이터 누수 방지
# 랜덤 분할 시 미래→과거 정보가 섞여 성능이 과대평가됨
train_df = df[df["date"] <= TRAIN_END_DATE].copy()
test_df = df[(df["date"] >= TEST_START_DATE) & (df["date"] <= TEST_END_DATE)].copy()

# 누수 검증: X에서 금지 컬럼이 포함되지 않았는지 확인
for col in FEATURE_COLS:
    assert col not in EXCLUDED_COLS, f"금지 컬럼 {col}이 피처에 포함됨!"
print("  누수 검증: X에 금지 컬럼 없음 ✓")

# 학습/평가 날짜 겹침 확인
train_dates = set(train_df["date"].unique())
test_dates = set(test_df["date"].unique())
assert len(train_dates & test_dates) == 0, "학습/평가 날짜 겹침!"
print("  날짜 겹침 검증: 없음 ✓")

# X, y 분리
X_train = train_df[FEATURE_COLS]
y_train = train_df[TARGET_COL]
X_test = test_df[FEATURE_COLS]
y_test = test_df[TARGET_COL]

print(f"\n  Train: {len(X_train):,}행 | 기간: {train_df['date'].min()} ~ {train_df['date'].max()} | PLU: {train_df['plu_code'].nunique():,}개")
print(f"  Test:  {len(X_test):,}행 | 기간: {test_df['date'].min()} ~ {test_df['date'].max()} | PLU: {test_df['plu_code'].nunique():,}개")
print(f"  피처 수: {len(FEATURE_COLS)}개")
print(f"  피처 목록: {FEATURE_COLS}")


# ============================================================
# 6. 모델 학습 (RandomForest Training)
# ============================================================
print("\n" + "=" * 70)
print("6단계: RandomForest 학습")
print("=" * 70)

model = RandomForestRegressor(**RF_PARAMS)
model.fit(X_train, y_train)

print(f"  학습 완료: {RF_PARAMS['n_estimators']}개 트리")
print(f"  파라미터: max_depth={RF_PARAMS['max_depth']}, "
      f"min_samples_split={RF_PARAMS['min_samples_split']}, "
      f"min_samples_leaf={RF_PARAMS['min_samples_leaf']}")


# ============================================================
# 7. 피처 중요도 (Feature Importance)
# ============================================================
print("\n" + "=" * 70)
print("7단계: 피처 중요도")
print("=" * 70)

# RF의 Gini Importance (불순도 감소량 기반)
importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)
importances = importances.sort_values(ascending=False)

for feat, imp in importances.items():
    bar = "█" * int(imp * 50)  # 시각화 바
    print(f"  {feat:<22s} {imp:.4f}  {bar}")


# ============================================================
# 8. 예측 및 평가 (Prediction & Evaluation)
# ============================================================
print("\n" + "=" * 70)
print("8단계: 예측 및 평가")
print("=" * 70)

# --- 8-1. RF 예측 ---
y_pred_raw = model.predict(X_test)
# 예측값 보정: 음수 → 0, 반올림하여 정수화
y_pred = np.maximum(0, np.round(y_pred_raw)).astype(int)

# --- 8-2. Naive 베이스라인 (lag_1) ---
# "내일 판매량 = 어제 판매량"이라는 가장 단순한 예측
y_naive = X_test["lag_1"].values


# --- 8-3. 평가 지표 계산 함수 ---
def calc_wape(actual, predicted):
    """WAPE: 매출 비중 가중 절대 오차율
    - sum(|pred - actual|) / sum(actual)
    - 판매량이 큰 상품의 오차에 더 민감 (실무적으로 유용)
    """
    total_actual = np.sum(actual)
    if total_actual == 0:
        return float("inf")
    return np.sum(np.abs(predicted - actual)) / total_actual


def calc_bias(actual, predicted):
    """Bias: 과대/과소 예측 경향
    - mean(pred - actual)
    - 양수: 과대예측 경향, 음수: 과소예측 경향
    """
    return np.mean(predicted - actual)


# --- 8-4. 전체(Overall) 성능 비교 ---
print("\n  [전체 성능 비교]")
print(f"  {'지표':<12s} {'RF 모델':>12s} {'Naive(lag_1)':>12s} {'개선율':>10s}")
print("  " + "-" * 50)

# WAPE
wape_rf = calc_wape(y_test.values, y_pred)
wape_naive = calc_wape(y_test.values, y_naive)
wape_improve = (1 - wape_rf / wape_naive) * 100 if wape_naive > 0 else 0
print(f"  {'WAPE':<12s} {wape_rf:>11.4f} {wape_naive:>12.4f} {wape_improve:>+9.1f}%")

# MAE
mae_rf = mean_absolute_error(y_test, y_pred)
mae_naive = mean_absolute_error(y_test, y_naive)
mae_improve = (1 - mae_rf / mae_naive) * 100 if mae_naive > 0 else 0
print(f"  {'MAE':<12s} {mae_rf:>11.4f} {mae_naive:>12.4f} {mae_improve:>+9.1f}%")

# Bias
bias_rf = calc_bias(y_test.values, y_pred)
bias_naive = calc_bias(y_test.values, y_naive)
print(f"  {'Bias':<12s} {bias_rf:>11.4f} {bias_naive:>12.4f} {'':>10s}")

# RF가 Naive보다 나은지 판정
if wape_rf < wape_naive:
    print(f"\n  ✓ RF가 Naive 대비 WAPE {abs(wape_improve):.1f}% 개선")
else:
    print(f"\n  ⚠ RF가 Naive보다 WAPE 성능이 낮음 → 피처 엔지니어링 재검토 필요")


# --- 8-5. category_m별 성능 비교 ---
print(f"\n  [category_m별 성능 (상위 10개, Test 건수 기준)]")
print(f"  {'cat_m':>6s} {'건수':>6s} {'WAPE_RF':>9s} {'WAPE_Naive':>11s} {'MAE_RF':>8s} {'MAE_Naive':>10s}")
print("  " + "-" * 55)

# category_m 디코딩하여 리포트
test_df = test_df.copy()
test_df["y_pred"] = y_pred
test_df["y_naive"] = y_naive
test_df["y_actual"] = y_test.values

cat_m_stats = []
for cat_m_code in test_df["category_m"].unique():
    mask = test_df["category_m"] == cat_m_code
    sub = test_df[mask]
    actual = sub["y_actual"].values
    pred = sub["y_pred"].values
    naive = sub["y_naive"].values

    cat_m_stats.append({
        "cat_m": cat_m_code,
        "count": len(sub),
        "wape_rf": calc_wape(actual, pred),
        "wape_naive": calc_wape(actual, naive),
        "mae_rf": mean_absolute_error(actual, pred),
        "mae_naive": mean_absolute_error(actual, naive),
    })

# 건수 기준 상위 10개 출력
cat_m_stats = sorted(cat_m_stats, key=lambda x: -x["count"])
for s in cat_m_stats[:10]:
    # LabelEncoder로 원래 이름 복원
    cat_name = le_cat_m.inverse_transform([s["cat_m"]])[0]
    # 이름이 너무 길면 자르기
    display_name = cat_name[:8] if len(str(cat_name)) > 8 else cat_name
    print(f"  {display_name:>8s} {s['count']:>5d} {s['wape_rf']:>9.4f} {s['wape_naive']:>11.4f} "
          f"{s['mae_rf']:>8.4f} {s['mae_naive']:>10.4f}")


# ============================================================
# 9. confidenceScore 산출 (Tree-based Confidence)
# ============================================================
print("\n" + "=" * 70)
print("9단계: confidenceScore 산출")
print("=" * 70)

# RF 내 개별 트리의 예측값을 수집하여 분산 기반 신뢰도 계산
# 트리 간 예측이 일치할수록(std 낮을수록) confidence 높음
tree_predictions = np.array([tree.predict(X_test) for tree in model.estimators_])
pred_std = np.std(tree_predictions, axis=0)       # 트리 간 예측 표준편차
pred_mean = np.mean(tree_predictions, axis=0)      # 트리 간 예측 평균

# confidence = 1 - (std / (mean + 1))
# +1은 분모가 0이 되는 것을 방지 (판매량 0 예측 시)
confidence_scores = np.clip(1 - (pred_std / (pred_mean + 1)), 0, 1)

print(f"  confidenceScore 통계:")
print(f"    mean: {confidence_scores.mean():.4f}")
print(f"    min:  {confidence_scores.min():.4f}")
print(f"    max:  {confidence_scores.max():.4f}")
print(f"    std:  {confidence_scores.std():.4f}")


# ============================================================
# 10. 발주 추천 계산 (Order Recommendation)
# ============================================================
print("\n" + "=" * 70)
print("10단계: 발주 추천 계산")
print("=" * 70)

# 발주 공식: max(0, ceil(predicted_sales + safety_stock - current_stock))
# 현재 재고(current_stock)는 외부 시스템에서 가져와야 하므로, 프로토타입에서는 0으로 가정
test_df["predicted_sales"] = y_pred
test_df["confidence_score"] = confidence_scores

# safety_stock은 원본 데이터에 이미 포함되어 있음
# current_stock은 프로토타입에서 0으로 가정 (실운영 시 재고 시스템 연동)
CURRENT_STOCK = 0

test_df["recommended_order"] = test_df.apply(
    lambda row: max(0, ceil(row["predicted_sales"] + row["safety_stock"] - CURRENT_STOCK)),
    axis=1
)

# 음수 발주 0건 검증
negative_orders = (test_df["recommended_order"] < 0).sum()
print(f"  음수 발주 검증: {negative_orders}건 (0이어야 함) ✓" if negative_orders == 0
      else f"  ⚠ 음수 발주 {negative_orders}건 발견!")
print(f"  발주 추천 통계:")
print(f"    총 건수: {len(test_df):,}")
print(f"    발주 0인 건: {(test_df['recommended_order'] == 0).sum():,}")
print(f"    평균 발주: {test_df['recommended_order'].mean():.2f}")
print(f"    최대 발주: {test_df['recommended_order'].max()}")


# ============================================================
# 11. API 페이로드 생성 (Sample JSON for Spring API)
# ============================================================
print("\n" + "=" * 70)
print("11단계: API 페이로드 샘플 생성")
print("=" * 70)

# 테스트 데이터의 마지막 날짜를 기준으로 샘플 페이로드 생성
sample_date = test_df["date"].max()
sample_target_date = test_df[test_df["date"] == sample_date]["target_date"].iloc[0]
sample_df = test_df[test_df["date"] == sample_date].copy()

# category_m별 그룹핑하여 API 구조에 맞게 변환
categories_payload = []
for cat_m_code in sorted(sample_df["category_m"].unique()):
    cat_products = sample_df[sample_df["category_m"] == cat_m_code]
    cat_name = le_cat_m.inverse_transform([cat_m_code])[0]

    products = []
    for _, row in cat_products.iterrows():
        products.append({
            "pluCode": str(row["plu_code"]),
            "predictedSales": int(row["predicted_sales"]),
            "recommendedOrder": int(row["recommended_order"]),
            "confidenceScore": round(float(row["confidence_score"]), 4),
        })

    total_order = sum(p["recommendedOrder"] for p in products)

    # AI 메시지: 카테고리별 간단 요약
    avg_confidence = np.mean([p["confidenceScore"] for p in products])
    ai_msg = (f"{cat_name} 카테고리 {len(products)}개 상품, "
              f"총 추천발주 {total_order}개, "
              f"평균 신뢰도 {avg_confidence:.0%}")

    categories_payload.append({
        "categoryName": cat_name,
        "totalRecommendedOrder": total_order,
        "aiMessage": ai_msg,
        "products": products,
    })

api_payload = {
    "targetDate": sample_target_date,
    "categories": categories_payload,
}

# JSON 유효성 검증
try:
    json_str = json.dumps(api_payload, ensure_ascii=False, indent=2)
    json.loads(json_str)  # 파싱 가능 여부 재검증
    print(f"  JSON 유효성: 통과 ✓")
    print(f"  targetDate: {sample_target_date}")
    print(f"  카테고리 수: {len(categories_payload)}")
    total_products = sum(len(c["products"]) for c in categories_payload)
    print(f"  총 상품 수: {total_products}")
    total_orders = sum(c["totalRecommendedOrder"] for c in categories_payload)
    print(f"  총 추천발주: {total_orders}")
except json.JSONDecodeError as e:
    print(f"  ⚠ JSON 유효성 실패: {e}")

# 샘플 JSON 파일로 저장 (첫 2개 카테고리만 출력)
print(f"\n  [API 페이로드 샘플 - 상위 2개 카테고리]")
sample_payload = {
    "targetDate": api_payload["targetDate"],
    "categories": api_payload["categories"][:2],
}
print(json.dumps(sample_payload, ensure_ascii=False, indent=2))


# ============================================================
# 12. 모델 및 인코더 저장 (Model Persistence)
# ============================================================
print("\n" + "=" * 70)
print("12단계: 모델 및 인코더 저장")
print("=" * 70)

import joblib
import os

SAVE_DIR = r"C:\Users\김민서\Desktop\saved_models"
os.makedirs(SAVE_DIR, exist_ok=True)

# 모델 저장
model_path = os.path.join(SAVE_DIR, "rf_sales_forecast_v4.pkl")
joblib.dump(model, model_path)
print(f"  모델 저장: {model_path}")

# LabelEncoder 저장 (운영 추론 시 동일 인코딩 필요)
encoders = {"category_l": le_cat_l, "category_m": le_cat_m}
encoder_path = os.path.join(SAVE_DIR, "label_encoders_v4.pkl")
joblib.dump(encoders, encoder_path)
print(f"  인코더 저장: {encoder_path}")

# 피처 목록 저장 (운영 시 동일 피처 순서 보장)
feature_path = os.path.join(SAVE_DIR, "feature_cols_v4.json")
with open(feature_path, "w", encoding="utf-8") as f:
    json.dump(FEATURE_COLS, f, ensure_ascii=False)
print(f"  피처 목록 저장: {feature_path}")

# 전체 API 페이로드 저장
payload_path = os.path.join(SAVE_DIR, "sample_payload_v4.json")
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(api_payload, f, ensure_ascii=False, indent=2)
print(f"  샘플 페이로드 저장: {payload_path}")


# ============================================================
# 13. 최종 요약 (Final Summary)
# ============================================================
print("\n" + "=" * 70)
print("최종 요약")
print("=" * 70)
print(f"  데이터: {DATA_PATH}")
print(f"  학습: {len(X_train):,}행 ({train_df['date'].min()} ~ {TRAIN_END_DATE})")
print(f"  평가: {len(X_test):,}행 ({TEST_START_DATE} ~ {TEST_END_DATE})")
print(f"  피처: {len(FEATURE_COLS)}개")
print(f"  WAPE: {wape_rf:.4f} (Naive: {wape_naive:.4f}, 개선: {wape_improve:+.1f}%)")
print(f"  MAE:  {mae_rf:.4f} (Naive: {mae_naive:.4f}, 개선: {mae_improve:+.1f}%)")
print(f"  Bias: {bias_rf:+.4f}")
print(f"  평균 confidenceScore: {confidence_scores.mean():.4f}")
print(f"  모델 저장 경로: {SAVE_DIR}")
print("=" * 70)
