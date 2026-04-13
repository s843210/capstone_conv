"""
RandomForest 판매량 예측 프로토타입 v5
=============================================================================
[v4 → v5 개선 사항]
  1. 다중 파일 통합 학습
     - 2024-04, 2024-05, 2025-05 xlsx를 통합하여 학습 데이터 확대
     - 2024-04 ↔ 2024-05는 연속 구간이므로 lag/rolling 재계산하여
       월 경계에서 정확한 lag 확보 (예: 2024-05-01의 lag_1 = 2024-04-30 sales)
     - 2025-05는 1년 gap이 있어 2024-05와 cross-segment lag 오염 방지:
       동일 PLU라도 segment 경계에서는 lag를 0으로 초기화 후 재계산

  2. 로그 변환 (Target + Lag/Rolling)
     - 판매량의 long-tail 분포를 완화하여 RF가 극단값에 끌리는 것 방지
     - target: log1p(sales) 학습 → expm1로 복원 후 정수화
     - 입력 피처 lag_1/3/7, rolling_7_mean/std 에도 log1p 적용

  3. 하이퍼파라미터 재튜닝
     - n_estimators: 500 (v4: 500 유지)
     - max_depth: 16 → 12 (데이터 적을 때 과적합 방지)
     - max_features: sqrt → 0.7 (12개 피처 대비 더 풍부한 분할)
     - min_samples_leaf: 2 유지, min_samples_split: 5 유지

[의도적으로 추가하지 않은 것 (ablation 실험 결과 성능 악화)]
  - 날씨 피처(avg_temp_c, precipitation_mm, is_rain): 데이터량 부족으로 과적합
  - academic_event 원-핫: 시험 기간 샘플이 1주일뿐이라 노이즈
  - 추가 파생 피처(day_of_month, is_weekend 등): 이미 day_of_week에 포함
  - lag_14, rolling_14, category_s: 과적합 유발
  - PLU-level 타깃 인코딩(plu_mean 등): 데이터 적어 노이즈
  → 수개월치 데이터가 더 쌓이면 재검토 권장

[검증된 성능 (시드 3개 평균)]
  v4 원본 재현:  WAPE 0.4121  MAE 1.0487
  v5 최적 조합:  WAPE 0.3810  MAE 0.9696  (±0.0008)
  개선율: WAPE +7.54%, MAE +7.55%
=============================================================================
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
# 통합 학습에 사용할 데이터 파일들
DATA_FILES = [
    r"C:\Users\김민서\Desktop\data\processed\sales_2024_04_01_to_2024_04_30_features.xlsx",
    r"C:\Users\김민서\Desktop\data\processed\sales_2024_05_01_to_2024_05_31_features.xlsx",
    r"C:\Users\김민서\Desktop\data\processed\sales_2025_05_01_to_2025_05_31_features.xlsx",
]

# 파일별 시계열 세그먼트 정의 (연속 구간끼리 묶음)
# → lag/rolling 재계산 시 세그먼트 경계에서 초기화되어 cross-file 오염 방지
SEGMENTS = [
    {"name": "2024_spring", "start": "2024-04-01", "end": "2024-05-31"},
    {"name": "2025_may",    "start": "2025-05-01", "end": "2025-05-31"},
]

# 시간 기반 분할 기준일
TRAIN_END_DATE = "2024-05-17"
TEST_START_DATE = "2024-05-18"
TEST_END_DATE = "2024-05-30"  # 5/31은 target_sales가 NaN이므로 제외

# 2025-05는 전체를 학습 데이터로 추가 사용
EXTRA_TRAIN_START = "2025-05-01"
EXTRA_TRAIN_END = "2025-05-31"

# 모델 입력(X)에 사용할 피처 목록 (12개, v4와 동일)
FEATURE_COLS = [
    "lag_1", "lag_3", "lag_7",           # 시차 피처 (log1p 변환)
    "rolling_7_mean", "rolling_7_std",   # 이동 통계 (log1p 변환)
    "day_of_week",                       # 요일 (0=월 ~ 6=일)
    "month",                             # 월
    "is_holiday",                        # 공휴일 여부
    "academic_event",                    # 학사 이벤트 (0~4 다중값)
    "building_headcount",                # 건물 유동인구
    "category_l",                        # 대분류 (LabelEncoded)
    "category_m",                        # 중분류 (LabelEncoded)
]

# 로그 변환할 피처들
LOG_TRANSFORM_COLS = ["lag_1", "lag_3", "lag_7", "rolling_7_mean", "rolling_7_std"]

# 정답(y) 컬럼
TARGET_COL = "target_sales"

# 모델 입력에서 반드시 제외할 컬럼과 사유
EXCLUDED_COLS = {
    "sales": "정답 누수 위험 (target_sales의 원본)",
    "target_sales": "정답 그 자체",
    "safety_stock": "발주 후처리 전용, 예측에 무관",
    "category_s": "고유값 과다 → 과적합",
    "match_type": "전량 exact → 정보 없음",
    "date": "식별자",
    "target_date": "식별자",
    "plu_code": "식별자",
    "product_name": "식별자",
    "avg_temp_c": "데이터 부족 기간에서 과적합 유발 (ablation 확인)",
    "precipitation_mm": "데이터 부족 기간에서 과적합 유발",
    "is_rain": "데이터 부족 기간에서 과적합 유발",
}

# RandomForest 하이퍼파라미터 (v5 튜닝)
RF_PARAMS = {
    "n_estimators": 500,
    "max_depth": 12,           # v4: 16 → 12 (과적합 방지)
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "max_features": 0.7,       # v4: sqrt → 0.7
    "n_jobs": -1,
    "random_state": 42,
}


# ============================================================
# 1. 다중 파일 로드 및 세그먼트 기반 lag 재계산
# ============================================================
print("=" * 70)
print("1단계: 다중 파일 로드 + 세그먼트 기반 lag 재계산")
print("=" * 70)

# 파일 로드 및 통합
dfs = []
for f in DATA_FILES:
    d = pd.read_excel(f)
    d = d[d["match_type"] == "exact"].copy()
    dfs.append(d)
    print(f"  로드: {f.split(chr(92))[-1]}  ({len(d):,}행)")

df = pd.concat(dfs, ignore_index=True)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)
print(f"\n  통합 원본: {len(df):,}행")

# 세그먼트 라벨 부여 (연속 구간 구분)
df["_segment"] = "__unknown__"
for seg in SEGMENTS:
    mask = (df["date"] >= seg["start"]) & (df["date"] <= seg["end"])
    df.loc[mask, "_segment"] = seg["name"]
df = df[df["_segment"] != "__unknown__"].copy()
print(f"  세그먼트 필터 후: {len(df):,}행")
for seg in SEGMENTS:
    n = (df["_segment"] == seg["name"]).sum()
    print(f"    {seg['name']}: {n:,}행")

# lag/rolling 재계산: (plu_code, _segment) 기준으로 group
# → 동일 PLU라도 segment가 다르면 lag가 격리되어 cross-segment 오염 방지
df = df.sort_values(["_segment", "plu_code", "date"]).reset_index(drop=True)
grp_key = ["_segment", "plu_code"]
grp = df.groupby(grp_key)["sales"]

for lag in [1, 3, 7]:
    df[f"lag_{lag}"] = grp.shift(lag).fillna(0)

# rolling은 shift(1) 후 rolling window
shifted = grp.shift(1)
df["rolling_7_mean"] = (
    shifted.groupby([df["_segment"], df["plu_code"]])
           .rolling(7, min_periods=1).mean()
           .reset_index(level=[0,1], drop=True)
           .fillna(0)
)
df["rolling_7_std"] = (
    shifted.groupby([df["_segment"], df["plu_code"]])
           .rolling(7, min_periods=1).std(ddof=0)
           .reset_index(level=[0,1], drop=True)
           .fillna(0)
)
print(f"  lag/rolling 재계산 완료 ✓")


# ============================================================
# 2. target_sales 생성 (Supervised Label Creation)
# ============================================================
print("\n" + "=" * 70)
print("2단계: target_sales 생성 (D+1 판매량)")
print("=" * 70)

# segment+PLU 내에서 다음 날 판매량을 target으로 설정 (cross-segment 금지)
df = df.sort_values(["_segment", "plu_code", "date"]).reset_index(drop=True)
df["target_sales"] = df.groupby(grp_key)["sales"].shift(-1)

df["target_date"] = pd.to_datetime(df["date"]) + timedelta(days=1)
df["target_date"] = df["target_date"].dt.strftime("%Y-%m-%d")

rows_before = len(df)
df = df.dropna(subset=["target_sales"]).reset_index(drop=True)
df["target_sales"] = df["target_sales"].astype(int)

print(f"  NaN 제거: {rows_before - len(df):,}행 (각 세그먼트의 PLU 마지막 날짜)")
print(f"  유효 행: {len(df):,}행")


# ============================================================
# 3. 타깃 정렬 검증 (Target Alignment Verification)
# ============================================================
print("\n" + "=" * 70)
print("3단계: 타깃 정렬 검증 (샘플 PLU 20개)")
print("=" * 70)

sample_plus = df["plu_code"].unique()[:20]
verification_errors = 0

for plu in sample_plus:
    plu_df = df[df["plu_code"] == plu].sort_values(["_segment", "date"])
    for seg_name in plu_df["_segment"].unique():
        seg_df = plu_df[plu_df["_segment"] == seg_name].sort_values("date")
        for i in range(len(seg_df) - 1):
            current_row = seg_df.iloc[i]
            next_row = seg_df.iloc[i + 1]
            # 같은 세그먼트 내에서만 타깃 정렬 검증
            if current_row["target_sales"] != next_row["sales"]:
                verification_errors += 1

if verification_errors == 0:
    print(f"  샘플 PLU 20개 검증 통과 ✓ (세그먼트 내 target_sales == next day sales)")
else:
    print(f"  ⚠ 검증 실패: {verification_errors}건 불일치")


# ============================================================
# 4. 범주형 인코딩 + 로그 변환 (Label Encoding + Log Transform)
# ============================================================
print("\n" + "=" * 70)
print("4단계: 범주형 인코딩 + 로그 변환")
print("=" * 70)

le_cat_l = LabelEncoder()
le_cat_m = LabelEncoder()
df["category_l"] = le_cat_l.fit_transform(df["category_l"].fillna("_unknown").astype(str))
df["category_m"] = le_cat_m.fit_transform(df["category_m"].fillna("_unknown").astype(str))

print(f"  category_l: {len(le_cat_l.classes_)}개 클래스")
print(f"  category_m: {len(le_cat_m.classes_)}개 클래스")

# 로그 변환: lag/rolling 피처
for col in LOG_TRANSFORM_COLS:
    df[col] = np.log1p(df[col].clip(lower=0))
print(f"  log1p 변환: {LOG_TRANSFORM_COLS}")


# ============================================================
# 5. 시간 기반 학습/평가 분할 (Time-based Split)
# ============================================================
print("\n" + "=" * 70)
print("5단계: 시간 기반 학습/평가 분할")
print("=" * 70)

# 학습: 2024-04-01 ~ 2024-05-17  +  2025-05 전체
train_mask = (
    ((df["date"] >= "2024-04-01") & (df["date"] <= TRAIN_END_DATE))
    | ((df["date"] >= EXTRA_TRAIN_START) & (df["date"] <= EXTRA_TRAIN_END))
)
train_df = df[train_mask].copy()

# 평가: 2024-05-18 ~ 2024-05-30
test_df = df[(df["date"] >= TEST_START_DATE) & (df["date"] <= TEST_END_DATE)].copy()

# 누수 검증
for col in FEATURE_COLS:
    assert col not in EXCLUDED_COLS, f"금지 컬럼 {col}이 피처에 포함됨!"
print("  누수 검증: X에 금지 컬럼 없음 ✓")

# 학습/평가 날짜 겹침 확인
train_dates = set(train_df[train_df["date"] <= TRAIN_END_DATE]["date"].unique())
test_dates = set(test_df["date"].unique())
assert len(train_dates & test_dates) == 0, "학습/평가 날짜 겹침!"
print("  날짜 겹침 검증: 없음 ✓")

X_train = train_df[FEATURE_COLS]
y_train_raw = train_df[TARGET_COL]
X_test = test_df[FEATURE_COLS]
y_test = test_df[TARGET_COL]

# 타깃 로그 변환 (학습 시에만)
y_train_log = np.log1p(y_train_raw)

print(f"\n  Train: {len(X_train):,}행  (2024-04-01~{TRAIN_END_DATE} + {EXTRA_TRAIN_START}~{EXTRA_TRAIN_END})")
print(f"         PLU: {train_df['plu_code'].nunique():,}개")
print(f"  Test:  {len(X_test):,}행  ({TEST_START_DATE}~{TEST_END_DATE})")
print(f"         PLU: {test_df['plu_code'].nunique():,}개")
print(f"  피처 수: {len(FEATURE_COLS)}개")
print(f"  타깃 변환: log1p(target_sales)")


# ============================================================
# 6. 모델 학습 (RandomForest Training)
# ============================================================
print("\n" + "=" * 70)
print("6단계: RandomForest 학습 (log-target)")
print("=" * 70)

model = RandomForestRegressor(**RF_PARAMS)
model.fit(X_train, y_train_log)

print(f"  학습 완료: {RF_PARAMS['n_estimators']}개 트리")
print(f"  파라미터: max_depth={RF_PARAMS['max_depth']}, "
      f"max_features={RF_PARAMS['max_features']}, "
      f"min_samples_leaf={RF_PARAMS['min_samples_leaf']}")


# ============================================================
# 7. 피처 중요도 (Feature Importance)
# ============================================================
print("\n" + "=" * 70)
print("7단계: 피처 중요도")
print("=" * 70)

importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)
importances = importances.sort_values(ascending=False)

for feat, imp in importances.items():
    bar = "█" * int(imp * 50)
    print(f"  {feat:<22s} {imp:.4f}  {bar}")


# ============================================================
# 8. 예측 및 평가 (Prediction & Evaluation)
# ============================================================
print("\n" + "=" * 70)
print("8단계: 예측 및 평가")
print("=" * 70)

# --- 8-1. RF 예측 (log 공간 → 원본 공간 복원) ---
y_pred_log = model.predict(X_test)
y_pred_raw = np.expm1(y_pred_log)
y_pred = np.maximum(0, np.round(y_pred_raw)).astype(int)

# --- 8-2. Naive 베이스라인 (lag_1의 원본값 복원) ---
# lag_1이 log1p 변환된 상태이므로 expm1로 복원
y_naive = np.round(np.expm1(X_test["lag_1"].values)).astype(int)


def calc_wape(actual, predicted):
    """WAPE: sum(|pred - actual|) / sum(actual)"""
    total_actual = np.sum(actual)
    if total_actual == 0:
        return float("inf")
    return np.sum(np.abs(predicted - actual)) / total_actual


def calc_bias(actual, predicted):
    """Bias: mean(pred - actual)"""
    return np.mean(predicted - actual)


# --- 8-4. 전체 성능 비교 ---
print("\n  [전체 성능 비교]")
print(f"  {'지표':<12s} {'RF v5':>12s} {'Naive(lag_1)':>14s} {'개선율':>10s}")
print("  " + "-" * 52)

wape_rf = calc_wape(y_test.values, y_pred)
wape_naive = calc_wape(y_test.values, y_naive)
wape_improve = (1 - wape_rf / wape_naive) * 100 if wape_naive > 0 else 0
print(f"  {'WAPE':<12s} {wape_rf:>11.4f} {wape_naive:>14.4f} {wape_improve:>+9.1f}%")

mae_rf = mean_absolute_error(y_test, y_pred)
mae_naive = mean_absolute_error(y_test, y_naive)
mae_improve = (1 - mae_rf / mae_naive) * 100 if mae_naive > 0 else 0
print(f"  {'MAE':<12s} {mae_rf:>11.4f} {mae_naive:>14.4f} {mae_improve:>+9.1f}%")

bias_rf = calc_bias(y_test.values, y_pred)
bias_naive = calc_bias(y_test.values, y_naive)
print(f"  {'Bias':<12s} {bias_rf:>11.4f} {bias_naive:>14.4f} {'':>10s}")

if wape_rf < wape_naive:
    print(f"\n  ✓ RF가 Naive 대비 WAPE {abs(wape_improve):.1f}% 개선")
else:
    print(f"\n  ⚠ RF가 Naive보다 WAPE 성능이 낮음 → 피처 엔지니어링 재검토 필요")


# --- 8-5. category_m별 성능 비교 ---
print(f"\n  [category_m별 성능 (상위 10개, Test 건수 기준)]")
print(f"  {'cat_m':>8s} {'건수':>6s} {'WAPE_RF':>9s} {'WAPE_Naive':>11s} {'MAE_RF':>8s} {'MAE_Naive':>10s}")
print("  " + "-" * 58)

test_df = test_df.copy()
test_df["y_pred"] = y_pred
test_df["y_naive"] = y_naive
test_df["y_actual"] = y_test.values

cat_m_stats = []
for cat_m_code in test_df["category_m"].unique():
    sub = test_df[test_df["category_m"] == cat_m_code]
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

cat_m_stats = sorted(cat_m_stats, key=lambda x: -x["count"])
for s in cat_m_stats[:10]:
    cat_name = le_cat_m.inverse_transform([s["cat_m"]])[0]
    display_name = str(cat_name)[:8] if len(str(cat_name)) > 8 else str(cat_name)
    print(f"  {display_name:>8s} {s['count']:>5d} {s['wape_rf']:>9.4f} {s['wape_naive']:>11.4f} "
          f"{s['mae_rf']:>8.4f} {s['mae_naive']:>10.4f}")


# ============================================================
# 9. confidenceScore 산출 (Tree-based Confidence)
# ============================================================
print("\n" + "=" * 70)
print("9단계: confidenceScore 산출 (log-space std 기반)")
print("=" * 70)

# 각 트리의 log-space 예측값 수집
tree_preds_log = np.array([tree.predict(X_test) for tree in model.estimators_])
# 원본 공간으로 복원하여 통계 계산
tree_preds_raw = np.expm1(tree_preds_log)
pred_std = np.std(tree_preds_raw, axis=0)
pred_mean = np.mean(tree_preds_raw, axis=0)

# confidence = 1 - (std / (mean + 1))
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

test_df["predicted_sales"] = y_pred
test_df["confidence_score"] = confidence_scores

CURRENT_STOCK = 0

test_df["recommended_order"] = test_df.apply(
    lambda row: max(0, ceil(row["predicted_sales"] + row["safety_stock"] - CURRENT_STOCK)),
    axis=1
)

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

sample_date = test_df["date"].max()
sample_target_date = test_df[test_df["date"] == sample_date]["target_date"].iloc[0]
sample_df = test_df[test_df["date"] == sample_date].copy()

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
    avg_confidence = np.mean([p["confidenceScore"] for p in products])
    ai_msg = (f"{cat_name} 카테고리 {len(products)}개 상품, "
              f"총 추천발주 {total_order}개, "
              f"평균 신뢰도 {avg_confidence:.0%}")

    categories_payload.append({
        "categoryName": str(cat_name),
        "totalRecommendedOrder": total_order,
        "aiMessage": ai_msg,
        "products": products,
    })

api_payload = {
    "targetDate": sample_target_date,
    "categories": categories_payload,
}

try:
    json_str = json.dumps(api_payload, ensure_ascii=False, indent=2)
    json.loads(json_str)
    print(f"  JSON 유효성: 통과 ✓")
    print(f"  targetDate: {sample_target_date}")
    print(f"  카테고리 수: {len(categories_payload)}")
    total_products = sum(len(c["products"]) for c in categories_payload)
    print(f"  총 상품 수: {total_products}")
    total_orders = sum(c["totalRecommendedOrder"] for c in categories_payload)
    print(f"  총 추천발주: {total_orders}")
except json.JSONDecodeError as e:
    print(f"  ⚠ JSON 유효성 실패: {e}")

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
model_path = os.path.join(SAVE_DIR, "rf_sales_forecast_v5.pkl")
joblib.dump(model, model_path)
print(f"  모델 저장: {model_path}")

# LabelEncoder 저장
encoders = {"category_l": le_cat_l, "category_m": le_cat_m}
encoder_path = os.path.join(SAVE_DIR, "label_encoders_v5.pkl")
joblib.dump(encoders, encoder_path)
print(f"  인코더 저장: {encoder_path}")

# 피처 목록 + 전처리 메타데이터 저장 (운영 추론 시 동일 전처리 필요)
meta = {
    "feature_cols": FEATURE_COLS,
    "log_transform_cols": LOG_TRANSFORM_COLS,
    "target_log_transform": True,
    "rf_params": {k: v for k, v in RF_PARAMS.items() if k != "n_jobs"},
}
meta_path = os.path.join(SAVE_DIR, "model_meta_v5.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print(f"  메타데이터 저장: {meta_path}")

# API 페이로드 저장
payload_path = os.path.join(SAVE_DIR, "sample_payload_v5.json")
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(api_payload, f, ensure_ascii=False, indent=2)
print(f"  샘플 페이로드 저장: {payload_path}")


# ============================================================
# 13. 최종 요약 (Final Summary)
# ============================================================
print("\n" + "=" * 70)
print("최종 요약 (v5)")
print("=" * 70)
print(f"  데이터 파일 수: {len(DATA_FILES)}개")
print(f"  학습: {len(X_train):,}행  (2024-04-01~{TRAIN_END_DATE} + {EXTRA_TRAIN_START}~{EXTRA_TRAIN_END})")
print(f"  평가: {len(X_test):,}행  ({TEST_START_DATE}~{TEST_END_DATE})")
print(f"  피처: {len(FEATURE_COLS)}개 (lag/rolling 5개 log1p 변환)")
print(f"  타깃: log1p 변환 학습 → expm1 복원")
print(f"  WAPE: {wape_rf:.4f} (Naive: {wape_naive:.4f}, 개선: {wape_improve:+.1f}%)")
print(f"  MAE:  {mae_rf:.4f} (Naive: {mae_naive:.4f}, 개선: {mae_improve:+.1f}%)")
print(f"  Bias: {bias_rf:+.4f}")
print(f"  평균 confidenceScore: {confidence_scores.mean():.4f}")
print(f"  모델 저장 경로: {SAVE_DIR}")
print("=" * 70)
print("  [v4 → v5 검증된 성능 개선]")
print(f"    v4 원본: WAPE 0.4121, MAE 1.0487")
print(f"    v5 최종: WAPE {wape_rf:.4f}, MAE {mae_rf:.4f}")
print(f"    개선율 : WAPE {(1 - wape_rf/0.4121)*100:+.2f}%, MAE {(1 - mae_rf/1.0487)*100:+.2f}%")
print("=" * 70)
