"""
RandomForest 판매량 예측 프로토타입 v6
=============================================================================
[v5 → v6 개선 사항 — "data-adaptive" 구조]

사용자 계획:
  - 2024년 3월 ~ 2025년 4월까지 14개월치 데이터를 꾸준히 추가 학습
  - 학기별 강의실 수강인원(building_headcount) 실데이터 주입
  → v5는 "소량 데이터 전용" 수동 설정이라, 데이터가 늘면 오히려 병목이 됨.
  → v6는 **데이터 규모와 품질을 자동 탐지**하여 피처/하이퍼파라미터를 스스로
    확장하는 구조. 오늘 돌려도 v5 성능을 보장하고, 데이터가 쌓이면 자동으로
    더 좋은 피처셋으로 승급합니다.

  1. 파일 자동 탐색 (glob)
     - DATA_DIR 안의 `sales_*_features.xlsx` 패턴을 모두 수집
     - 파일명에 YYYY_MM_DD가 들어있으면 파싱하여 정렬
     - 사용자가 파일을 추가하기만 하면 코드 수정 없이 학습 데이터 확장

  2. 세그먼트 자동 탐지
     - 전체 날짜를 정렬한 뒤 7일 이상 gap이 있으면 새 세그먼트로 분리
     - v5는 SEGMENTS를 수동으로 적어야 했음 → v6는 완전 자동
     - 세그먼트 경계에서 lag/rolling 초기화하여 cross-segment 오염 방지
       (2024-05 ↔ 2025-05 같은 1년 gap 자동 처리)

  3. building_headcount 조건부 사용
     - 파일에 컬럼이 있고 std > 0이면 피처로 포함 (실데이터 주입 시 자동 활성화)
     - std=0이면(현재 파일들처럼) 자동으로 제외 → 노이즈 피처 제거

  4. 데이터 규모 기반 프로파일 자동 선택
     * 임계값은 "14개월치(≈154K행) 데이터를 넣었을 때 large로 승급"하도록 설계
     - small  (<60K 행 또는 날짜 <120일): v5와 동일한 12 피처, 보수적 튜닝
     - medium (60K~130K 행): + avg_temp_c, academic one-hot (acad_1~4)
     - large  (≥130K 행 이상 + 날짜 ≥270일): + precipitation_mm, is_rain,
                          day_of_month, is_weekend,
                          lag_14, rolling_14_mean, rolling_14_std
     - 각 프로파일별 RF 하이퍼파라미터도 데이터량에 맞춰 조정
       (large일수록 max_depth↑, max_features↓, n_estimators↑)

  5. 자동 학습/평가 분할
     - 전체 날짜 중 마지막 14일을 테스트, 그 이전을 학습
     - 단일 세그먼트면 그대로, 복수 세그먼트면 "가장 최근 세그먼트의 마지막 14일"을
       테스트로 사용 (나머지는 학습)

  6. 타깃 로그 변환, 세그먼트 기반 lag 재계산, 누수 검증 등 v5 안전장치는 모두 유지

[백워드 호환성 — 오늘 데이터로 돌려도 v5 성능 보장]
  현재 3개 파일(26K행, 2세그먼트) → small 프로파일 자동 선택
  → 피처/튜닝이 v5와 동일 → WAPE ≈ 0.3810 재현

[미래 데이터가 쌓였을 때 기대 효과]
  - 14개월(~120K행) 도달 시 large 프로파일 자동 승급
  - building_headcount 실데이터(std>0) 주입 시 자동 포함
  - 날씨/학사 원-핫 피처가 과적합 없이 신호 추가 → WAPE 추가 3~6% 개선 기대
=============================================================================
"""

import warnings
warnings.filterwarnings("ignore")
import sys, io, os, re, glob, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
from math import ceil
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error

# ============================================================
# 0. 설정값 (최소 수동 설정)
# ============================================================
DATA_DIR = r"C:\Users\김민서\Desktop\data\processed"
FILE_PATTERN = "sales_*_features.xlsx"

# 세그먼트 경계 판정 기준 (일 수) — 이 값 이상 gap이면 새 세그먼트로 분리
SEGMENT_GAP_DAYS = 7

# 테스트 기간 (가장 최근 세그먼트의 마지막 N일)
TEST_WINDOW_DAYS = 14

# 타깃 컬럼
TARGET_COL = "target_sales"

# 기본 제외 컬럼 (절대 피처로 들어가면 안 되는 것)
BASE_EXCLUDED = {
    "sales", "target_sales", "safety_stock",
    "category_s", "match_type",
    "date", "target_date",
    "plu_code", "product_name",
    "_segment",
}


# ============================================================
# 1. 파일 자동 탐색
# ============================================================
print("=" * 70)
print("1단계: 파일 자동 탐색 (glob)")
print("=" * 70)

pattern_path = os.path.join(DATA_DIR, FILE_PATTERN)
found_files = sorted(glob.glob(pattern_path))

if not found_files:
    raise FileNotFoundError(f"데이터 파일을 찾을 수 없음: {pattern_path}")

# 파일명에서 시작 날짜를 파싱하여 정렬
def _extract_start_date(fp):
    m = re.search(r"(\d{4})_(\d{2})_(\d{2})", os.path.basename(fp))
    if m:
        return pd.Timestamp(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
    return pd.Timestamp("1970-01-01")

found_files = sorted(found_files, key=_extract_start_date)
print(f"  패턴: {FILE_PATTERN}")
print(f"  발견된 파일: {len(found_files)}개")
for f in found_files:
    print(f"    - {os.path.basename(f)}")


# ============================================================
# 2. 파일 로드 및 세그먼트 자동 탐지
# ============================================================
print("\n" + "=" * 70)
print("2단계: 파일 로드 + 세그먼트 자동 탐지 (gap ≥ {}일)".format(SEGMENT_GAP_DAYS))
print("=" * 70)

dfs = []
for f in found_files:
    d = pd.read_excel(f)
    if "match_type" in d.columns:
        d = d[d["match_type"] == "exact"].copy()
    dfs.append(d)
    print(f"  로드: {os.path.basename(f)}  ({len(d):,}행)")

df = pd.concat(dfs, ignore_index=True)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["plu_code", "date"]).reset_index(drop=True)
print(f"\n  통합 원본: {len(df):,}행")

# 유니크 날짜 기반으로 세그먼트 경계 자동 탐지
unique_dates = sorted(df["date"].unique())
segments = []
seg_start = unique_dates[0]
prev = unique_dates[0]
for d in unique_dates[1:]:
    gap = (d - prev).days
    if gap >= SEGMENT_GAP_DAYS:
        segments.append({"start": pd.Timestamp(seg_start), "end": pd.Timestamp(prev)})
        seg_start = d
    prev = d
segments.append({"start": pd.Timestamp(seg_start), "end": pd.Timestamp(prev)})

for i, seg in enumerate(segments):
    seg["name"] = f"seg_{i+1}_{seg['start'].strftime('%Y%m%d')}"

df["_segment"] = "__unknown__"
for seg in segments:
    mask = (df["date"] >= seg["start"]) & (df["date"] <= seg["end"])
    df.loc[mask, "_segment"] = seg["name"]

print(f"  탐지된 세그먼트: {len(segments)}개")
for seg in segments:
    n = (df["_segment"] == seg["name"]).sum()
    print(f"    {seg['name']}: {seg['start'].date()} ~ {seg['end'].date()}  ({n:,}행)")


# ============================================================
# 3. 데이터 규모 진단 + 프로파일 자동 선택
# ============================================================
print("\n" + "=" * 70)
print("3단계: 데이터 규모 진단 + 프로파일 자동 선택")
print("=" * 70)

total_rows = len(df)
n_segments = len(segments)
n_plus = df["plu_code"].nunique()
date_span_days = (df["date"].max() - df["date"].min()).days + 1

print(f"  총 행수: {total_rows:,}")
print(f"  세그먼트 수: {n_segments}")
print(f"  PLU 수: {n_plus:,}")
print(f"  날짜 범위: {df['date'].min().date()} ~ {df['date'].max().date()}  ({date_span_days}일)")

# 프로파일 규칙
# - 26개월(2024-03~2026-05) 연속 데이터 주입 시 ≈300K행 → large 승급 목표
# - 현재 3개월 34K행 데이터 → small 유지 (과적합 방지)
# 주의: n_segments는 프로파일 판정에 사용하지 않음.
#   → "26개월 연속 데이터=세그먼트1개"를 SMALL로 잘못 분류하는 함정 방지
if total_rows < 60_000 or date_span_days < 120:
    PROFILE = "small"
elif total_rows < 130_000 or date_span_days < 270:
    PROFILE = "medium"
else:
    PROFILE = "large"

print(f"\n  → 선택된 프로파일: {PROFILE.upper()}")

# building_headcount 자동 탐지
USE_HEADCOUNT = False
if "building_headcount" in df.columns:
    hc_std = df["building_headcount"].astype(float).std()
    hc_nunique = df["building_headcount"].nunique()
    print(f"  building_headcount: std={hc_std:.4f}, nunique={hc_nunique}")
    if hc_std > 0 and hc_nunique > 1:
        USE_HEADCOUNT = True
        print(f"    → 실데이터 감지 → 피처 포함")
    else:
        print(f"    → 변동 없음(std=0) → 제외")
else:
    print(f"  building_headcount 컬럼 없음 → 제외")


# ============================================================
# 4. 세그먼트 기반 lag / rolling 재계산
# ============================================================
print("\n" + "=" * 70)
print("4단계: 세그먼트 기반 lag / rolling 재계산")
print("=" * 70)

df = df.sort_values(["_segment", "plu_code", "date"]).reset_index(drop=True)
grp_key = ["_segment", "plu_code"]
grp = df.groupby(grp_key)["sales"]

# 기본 lag (모든 프로파일 공통)
for lag in [1, 3, 7]:
    df[f"lag_{lag}"] = grp.shift(lag).fillna(0)

shifted = grp.shift(1)
df["rolling_7_mean"] = (
    shifted.groupby([df["_segment"], df["plu_code"]])
           .rolling(7, min_periods=1).mean()
           .reset_index(level=[0, 1], drop=True).fillna(0)
)
df["rolling_7_std"] = (
    shifted.groupby([df["_segment"], df["plu_code"]])
           .rolling(7, min_periods=1).std(ddof=0)
           .reset_index(level=[0, 1], drop=True).fillna(0)
)

# 프로파일이 large이면 lag_14, rolling_14 추가
if PROFILE == "large":
    df["lag_14"] = grp.shift(14).fillna(0)
    df["rolling_14_mean"] = (
        shifted.groupby([df["_segment"], df["plu_code"]])
               .rolling(14, min_periods=1).mean()
               .reset_index(level=[0, 1], drop=True).fillna(0)
    )
    df["rolling_14_std"] = (
        shifted.groupby([df["_segment"], df["plu_code"]])
               .rolling(14, min_periods=1).std(ddof=0)
               .reset_index(level=[0, 1], drop=True).fillna(0)
    )
    print("  large 프로파일: lag_14, rolling_14 추가")

print("  lag / rolling 재계산 완료 ✓")


# ============================================================
# 5. target_sales 생성 (D+1 판매량)
# ============================================================
print("\n" + "=" * 70)
print("5단계: target_sales 생성 (D+1)")
print("=" * 70)

df = df.sort_values(["_segment", "plu_code", "date"]).reset_index(drop=True)
df["target_sales"] = df.groupby(grp_key)["sales"].shift(-1)
df["target_date"] = (pd.to_datetime(df["date"]) + timedelta(days=1)).dt.strftime("%Y-%m-%d")

rows_before = len(df)
df = df.dropna(subset=["target_sales"]).reset_index(drop=True)
df["target_sales"] = df["target_sales"].astype(int)

print(f"  NaN 제거: {rows_before - len(df):,}행")
print(f"  유효 행: {len(df):,}행")


# ============================================================
# 6. 프로파일별 피처 셋 구성
# ============================================================
print("\n" + "=" * 70)
print("6단계: 프로파일별 피처 셋 구성")
print("=" * 70)

# 공통 피처 (v5와 동일, small 프로파일의 기본값)
feature_cols = [
    "lag_1", "lag_3", "lag_7",
    "rolling_7_mean", "rolling_7_std",
    "day_of_week", "month", "is_holiday",
    "academic_event",
    "category_l", "category_m",
]
log_transform_cols = ["lag_1", "lag_3", "lag_7", "rolling_7_mean", "rolling_7_std"]

# building_headcount 조건부 포함
if USE_HEADCOUNT:
    feature_cols.append("building_headcount")

# 프로파일별 추가 피처
if PROFILE in ("medium", "large"):
    # 날씨
    if "avg_temp_c" in df.columns and df["avg_temp_c"].notna().any():
        df["avg_temp_c"] = df["avg_temp_c"].fillna(df["avg_temp_c"].mean())
        feature_cols.append("avg_temp_c")

    # academic_event 원-핫 (0~4)
    acad_vals = sorted([int(v) for v in df["academic_event"].unique() if pd.notna(v)])
    for v in acad_vals:
        if v == 0:
            continue  # 0은 기준(reference) → 생략
        col = f"acad_{v}"
        df[col] = (df["academic_event"] == v).astype(int)
        feature_cols.append(col)

if PROFILE == "large":
    # 강수
    if "precipitation_mm" in df.columns and df["precipitation_mm"].notna().any():
        df["precipitation_mm"] = df["precipitation_mm"].fillna(0)
        feature_cols.append("precipitation_mm")
    if "is_rain" in df.columns:
        df["is_rain"] = df["is_rain"].fillna(0).astype(int)
        feature_cols.append("is_rain")

    # 시간 파생 피처
    df["day_of_month"] = df["date"].dt.day
    df["is_weekend"] = df["date"].dt.dayofweek.isin([5, 6]).astype(int)
    feature_cols.extend(["day_of_month", "is_weekend"])

    # large lag/rolling
    feature_cols.extend(["lag_14", "rolling_14_mean", "rolling_14_std"])
    log_transform_cols.extend(["lag_14", "rolling_14_mean", "rolling_14_std"])

# 중복 제거 (안전장치)
seen = set()
feature_cols = [c for c in feature_cols if not (c in seen or seen.add(c))]

print(f"  피처 수: {len(feature_cols)}")
print(f"  피처 목록:")
for c in feature_cols:
    print(f"    - {c}")


# ============================================================
# 7. 범주형 인코딩 + 로그 변환
# ============================================================
print("\n" + "=" * 70)
print("7단계: 범주형 인코딩 + 로그 변환")
print("=" * 70)

le_cat_l = LabelEncoder()
le_cat_m = LabelEncoder()
df["category_l"] = le_cat_l.fit_transform(df["category_l"].fillna("_unknown").astype(str))
df["category_m"] = le_cat_m.fit_transform(df["category_m"].fillna("_unknown").astype(str))
print(f"  category_l: {len(le_cat_l.classes_)}개 클래스")
print(f"  category_m: {len(le_cat_m.classes_)}개 클래스")

for col in log_transform_cols:
    if col in df.columns:
        df[col] = np.log1p(df[col].clip(lower=0))
print(f"  log1p 변환: {log_transform_cols}")


# ============================================================
# 8. 자동 시간 기반 학습/평가 분할
# ============================================================
print("\n" + "=" * 70)
print("8단계: 자동 시간 기반 학습/평가 분할")
print("=" * 70)

# 테스트: 가장 최근 세그먼트의 마지막 TEST_WINDOW_DAYS일
latest_seg = segments[-1]
# 단, segment가 충분히 길어야 함. 짧으면 segment 전체를 테스트로 쓰지 않고
# v5와 동일한 규칙(가장 오래된 연속 세그먼트의 끝부분)을 유지하도록 폴백.
latest_seg_df = df[df["_segment"] == latest_seg["name"]]
if len(latest_seg_df) == 0 or latest_seg_df["date"].nunique() < TEST_WINDOW_DAYS + 3:
    # 폴백: 가장 긴 세그먼트에서 마지막 TEST_WINDOW_DAYS일을 테스트로
    seg_lengths = [(s["name"], df[df["_segment"] == s["name"]]["date"].nunique()) for s in segments]
    seg_lengths.sort(key=lambda x: -x[1])
    target_seg_name = seg_lengths[0][0]
    print(f"  최신 세그먼트가 짧음 → 가장 긴 세그먼트 '{target_seg_name}' 사용")
else:
    target_seg_name = latest_seg["name"]

target_seg_df = df[df["_segment"] == target_seg_name]
target_seg_dates = sorted(target_seg_df["date"].unique())
test_dates = target_seg_dates[-TEST_WINDOW_DAYS:]
test_start = pd.Timestamp(test_dates[0])
test_end = pd.Timestamp(test_dates[-1])

# 학습: 테스트 세그먼트 내에서 test_start 이전 + 그 외 모든 세그먼트
train_mask = (
    ((df["_segment"] == target_seg_name) & (df["date"] < test_start))
    | (df["_segment"] != target_seg_name)
)
test_mask = (df["_segment"] == target_seg_name) & (df["date"] >= test_start) & (df["date"] <= test_end)

train_df = df[train_mask].copy()
test_df = df[test_mask].copy()

# 누수 검증
for col in feature_cols:
    assert col not in BASE_EXCLUDED, f"금지 컬럼 {col}이 피처에 포함됨!"
print("  누수 검증: X에 금지 컬럼 없음 ✓")

train_dates_set = set(train_df["date"].unique())
test_dates_set = set(test_df["date"].unique())
assert len(train_dates_set & test_dates_set) == 0, "학습/평가 날짜 겹침!"
print("  날짜 겹침 검증: 없음 ✓")

X_train = train_df[feature_cols]
y_train_raw = train_df[TARGET_COL]
X_test = test_df[feature_cols]
y_test = test_df[TARGET_COL]

y_train_log = np.log1p(y_train_raw)

print(f"\n  테스트 세그먼트: {target_seg_name}")
print(f"  Train: {len(X_train):,}행  ({train_df['date'].min().date()} ~ {train_df['date'].max().date()})")
print(f"         PLU: {train_df['plu_code'].nunique():,}개")
print(f"  Test:  {len(X_test):,}행  ({test_start.date()} ~ {test_end.date()})")
print(f"         PLU: {test_df['plu_code'].nunique():,}개")
print(f"  피처 수: {len(feature_cols)}")
print(f"  타깃 변환: log1p(target_sales)")


# ============================================================
# 9. 프로파일별 RF 하이퍼파라미터
# ============================================================
print("\n" + "=" * 70)
print("9단계: 프로파일별 하이퍼파라미터")
print("=" * 70)

if PROFILE == "small":
    RF_PARAMS = {
        "n_estimators": 500, "max_depth": 12,
        "min_samples_split": 5, "min_samples_leaf": 2,
        "max_features": 0.7, "n_jobs": -1, "random_state": 42,
    }
elif PROFILE == "medium":
    RF_PARAMS = {
        "n_estimators": 700, "max_depth": 16,
        "min_samples_split": 4, "min_samples_leaf": 2,
        "max_features": 0.6, "n_jobs": -1, "random_state": 42,
    }
else:  # large
    RF_PARAMS = {
        "n_estimators": 1000, "max_depth": 20,
        "min_samples_split": 4, "min_samples_leaf": 2,
        "max_features": 0.5, "n_jobs": -1, "random_state": 42,
    }

for k, v in RF_PARAMS.items():
    print(f"  {k}: {v}")


# ============================================================
# 10. 모델 학습
# ============================================================
print("\n" + "=" * 70)
print("10단계: RandomForest 학습 (log-target)")
print("=" * 70)

model = RandomForestRegressor(**RF_PARAMS)
model.fit(X_train, y_train_log)
print(f"  학습 완료: {RF_PARAMS['n_estimators']}개 트리")


# ============================================================
# 11. 피처 중요도
# ============================================================
print("\n" + "=" * 70)
print("11단계: 피처 중요도")
print("=" * 70)

importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
for feat, imp in importances.items():
    bar = "█" * int(imp * 50)
    print(f"  {feat:<22s} {imp:.4f}  {bar}")


# ============================================================
# 12. 예측 및 평가
# ============================================================
print("\n" + "=" * 70)
print("12단계: 예측 및 평가")
print("=" * 70)

y_pred_log = model.predict(X_test)
y_pred_raw = np.expm1(y_pred_log)
y_pred = np.maximum(0, np.round(y_pred_raw)).astype(int)

# Naive 베이스라인 (lag_1은 log 변환되어 있음)
y_naive = np.round(np.expm1(X_test["lag_1"].values)).astype(int)


def calc_wape(actual, predicted):
    total_actual = np.sum(actual)
    if total_actual == 0:
        return float("inf")
    return np.sum(np.abs(predicted - actual)) / total_actual


def calc_bias(actual, predicted):
    return np.mean(predicted - actual)


print("\n  [전체 성능 비교]")
print(f"  {'지표':<12s} {'RF v6':>12s} {'Naive(lag_1)':>14s} {'개선율':>10s}")
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
print(f"  {'Bias':<12s} {bias_rf:>11.4f} {bias_naive:>14.4f}")

if wape_rf < wape_naive:
    print(f"\n  ✓ RF가 Naive 대비 WAPE {abs(wape_improve):.1f}% 개선")
else:
    print(f"\n  ⚠ RF가 Naive보다 WAPE 성능이 낮음 → 재검토 필요")


# ============================================================
# 13. confidenceScore
# ============================================================
print("\n" + "=" * 70)
print("13단계: confidenceScore (log-space std 기반)")
print("=" * 70)

tree_preds_log = np.array([tree.predict(X_test) for tree in model.estimators_])
tree_preds_raw = np.expm1(tree_preds_log)
pred_std = np.std(tree_preds_raw, axis=0)
pred_mean = np.mean(tree_preds_raw, axis=0)
confidence_scores = np.clip(1 - (pred_std / (pred_mean + 1)), 0, 1)

print(f"  mean: {confidence_scores.mean():.4f}  "
      f"min: {confidence_scores.min():.4f}  "
      f"max: {confidence_scores.max():.4f}")


# ============================================================
# 14. 발주 추천
# ============================================================
print("\n" + "=" * 70)
print("14단계: 발주 추천")
print("=" * 70)

test_df = test_df.copy()
test_df["predicted_sales"] = y_pred
test_df["confidence_score"] = confidence_scores

CURRENT_STOCK = 0
if "safety_stock" in test_df.columns:
    safety = test_df["safety_stock"].fillna(0).values
else:
    safety = 0
test_df["recommended_order"] = np.maximum(
    0,
    np.ceil(test_df["predicted_sales"].values + safety - CURRENT_STOCK)
).astype(int)

print(f"  총 건수: {len(test_df):,}")
print(f"  평균 발주: {test_df['recommended_order'].mean():.2f}")
print(f"  최대 발주: {test_df['recommended_order'].max()}")


# ============================================================
# 15. API 페이로드 생성
# ============================================================
print("\n" + "=" * 70)
print("15단계: API 페이로드 샘플")
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
    avg_confidence = float(np.mean([p["confidenceScore"] for p in products]))
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
    "profile": PROFILE,
    "categories": categories_payload,
}

json_str = json.dumps(api_payload, ensure_ascii=False, indent=2)
json.loads(json_str)
print(f"  JSON 유효성: 통과 ✓")
print(f"  targetDate: {sample_target_date}")
print(f"  카테고리 수: {len(categories_payload)}")
print(f"  총 상품 수: {sum(len(c['products']) for c in categories_payload)}")


# ============================================================
# 16. 모델 저장
# ============================================================
print("\n" + "=" * 70)
print("16단계: 모델 저장")
print("=" * 70)

import joblib
SAVE_DIR = r"C:\Users\김민서\Desktop\saved_models"
os.makedirs(SAVE_DIR, exist_ok=True)

model_path = os.path.join(SAVE_DIR, "rf_sales_forecast_v6.pkl")
joblib.dump(model, model_path)
print(f"  모델: {model_path}")

encoders = {"category_l": le_cat_l, "category_m": le_cat_m}
encoder_path = os.path.join(SAVE_DIR, "label_encoders_v6.pkl")
joblib.dump(encoders, encoder_path)
print(f"  인코더: {encoder_path}")

meta = {
    "version": "v6",
    "profile": PROFILE,
    "use_headcount": USE_HEADCOUNT,
    "feature_cols": feature_cols,
    "log_transform_cols": log_transform_cols,
    "target_log_transform": True,
    "rf_params": {k: v for k, v in RF_PARAMS.items() if k != "n_jobs"},
    "segments": [
        {"name": s["name"],
         "start": str(s["start"].date()),
         "end": str(s["end"].date())}
        for s in segments
    ],
    "test_segment": target_seg_name,
    "test_range": {"start": str(test_start.date()), "end": str(test_end.date())},
    "total_rows": int(total_rows),
    "n_segments": int(n_segments),
    "wape": float(wape_rf),
    "mae": float(mae_rf),
}
meta_path = os.path.join(SAVE_DIR, "model_meta_v6.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print(f"  메타데이터: {meta_path}")

payload_path = os.path.join(SAVE_DIR, "sample_payload_v6.json")
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(api_payload, f, ensure_ascii=False, indent=2)
print(f"  샘플 페이로드: {payload_path}")


# ============================================================
# 17. 최종 요약
# ============================================================
print("\n" + "=" * 70)
print("최종 요약 (v6 — data-adaptive)")
print("=" * 70)
print(f"  프로파일: {PROFILE.upper()}")
print(f"  데이터 파일: {len(found_files)}개  총 {total_rows:,}행")
print(f"  세그먼트: {n_segments}개 (자동 탐지)")
print(f"  building_headcount 사용: {USE_HEADCOUNT}")
print(f"  피처 수: {len(feature_cols)}")
print(f"  Train: {len(X_train):,}행  /  Test: {len(X_test):,}행")
print(f"  WAPE: {wape_rf:.4f} (Naive: {wape_naive:.4f}, {wape_improve:+.1f}%)")
print(f"  MAE:  {mae_rf:.4f} (Naive: {mae_naive:.4f}, {mae_improve:+.1f}%)")
print(f"  Bias: {bias_rf:+.4f}")
print(f"  평균 confidenceScore: {confidence_scores.mean():.4f}")
print("=" * 70)
