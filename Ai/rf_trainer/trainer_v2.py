"""
trainer_v2.py  ─  에러없조 | Random Forest 수요 예측 모델 학습기
=============================================================================
[v1 → v2 개선 사항]
  1. 유효 피처 자동 필터링
     - 분산이 0인 피처(값이 전부 같은 컬럼)는 자동 제외
     - academic_event, building_headcount가 전부 0이면 학습에서 제외
     - 피처 목록을 model_meta.json에 저장해서 FastAPI가 동일 피처로 예측
  2. 시계열 교차검증 추가 (TimeSeriesSplit)
     - 테스트 연도 없을 때 교차검증으로 성능 추정
     - 실제 운영 성능과 가장 가까운 평가 방식
  3. 과적합 판단 개선
     - 훈련/테스트 MAE 비율로 과적합 수치화
  4. 학습 데이터 경로 유연화
     - data/processed 자동 탐색 + 직접 지정 모두 지원
  5. 전체 주석 및 로그 가독성 개선

[학습 전략 — 시계열 분할]
  훈련(Train) : 24년 데이터  → 모델이 패턴 학습
  테스트(Test): 25년 데이터  → 실제 운영 성능 검증
  ※ 랜덤 분리(train_test_split) 금지 — 미래 데이터로 과거 학습 = Data Leakage

[피처 구성 (Phase 0~1)]
  판매 시계열: lag_1, lag_3, lag_7, rolling_7_mean, rolling_7_std
  캘린더:      day_of_week, month, is_holiday, safety_stock
  카테고리:    category_m (라벨 인코딩)
  Phase 2+:   academic_event, building_headcount (데이터 확보 후 자동 활성화)

[사용법]
  터미널
    python trainer_v2.py                              # data/processed 자동 탐색
    python trainer_v2.py --data data/processed        # 폴더 지정
    python trainer_v2.py --train-years 2024 --test-years 2025
  Colab
    from trainer_v2 import run
    run(data_dir='data/processed', train_years=[2024], test_years=[2025])
=============================================================================
"""

import argparse
import json
import shutil
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════
# ① 상수 및 설정
# ══════════════════════════════════════════════

MODEL_DIR = Path("saved_models")

# 후보 피처 목록 — 분산이 0인 피처는 학습 전 자동 제외됨
CANDIDATE_FEATURES = [
    "lag_1",             # 어제 판매량
    "lag_3",             # 3일 전 판매량
    "lag_7",             # 7일 전 판매량 (동일 요일)
    "rolling_7_mean",    # 최근 7일 평균
    "rolling_7_std",     # 최근 7일 변동성
    "day_of_week",       # 요일 (월=0, 일=6)
    "month",             # 월 (1~12)
    "is_holiday",        # 공휴일/주말 여부
    "safety_stock",      # 카테고리별 안전재고 기준값
    "academic_event",    # 학사 이벤트 (Phase 2: 0=평상/1=시험/2=축제/3=방학)
    "building_headcount",# 건물 수강인원 (Phase 2: 시간표 CSV 기반)
    "category_encoded",  # 카테고리 라벨 인코딩
]

TARGET = "sales"

RF_PARAMS = {
    "n_estimators":   100,
    "max_depth":      10,
    "min_samples_leaf": 3,
    "max_features":   "sqrt",
    "random_state":   42,
    "n_jobs":         -1,
}


# ══════════════════════════════════════════════
# ② 데이터 로드
# ══════════════════════════════════════════════

def load_features(data_path: str) -> pd.DataFrame:
    """
    converter_v3.py가 만든 features CSV/XLSX 로드.
    여러 파일이 있으면 전부 합쳐서 반환.
    """
    path = Path(data_path)
    all_frames = []

    if path.is_dir():
        targets = sorted(path.glob("*features*.csv"))
        if not targets:
            targets = sorted(path.glob("*features*.xlsx"))
        if not targets:
            raise FileNotFoundError(
                f"'{data_path}' 폴더에 features 파일이 없습니다.\n"
                "converter_v3.py를 먼저 실행하세요."
            )
        print(f"  features 파일 {len(targets)}개 탐지:")
        for f in targets:
            print(f"    - {f.name}")
            all_frames.append(_read_one(str(f)))
    elif path.exists():
        print(f"  파일 로드: {path.name}")
        all_frames.append(_read_one(str(path)))
    else:
        raise FileNotFoundError(f"파일/폴더를 찾을 수 없습니다: {data_path}")

    df = pd.concat(all_frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    key = "plu_code" if "plu_code" in df.columns else "product_name"
    df = (df.sort_values("date")
            .drop_duplicates(subset=["date", key], keep="last")
            .reset_index(drop=True))

    if "plu_code" in df.columns:
        df["plu_code"] = df["plu_code"].fillna("").astype(str).str.strip()

    years = df["date"].dt.year.unique().tolist()
    print(f"  ✅ {len(df):,}행 로드 | 연도: {sorted(years)} | "
          f"상품: {df[key].nunique():,}개")
    return df


def _read_one(path: str) -> pd.DataFrame:
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        try:
            return pd.read_csv(path, dtype={"plu_code": str}, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, dtype={"plu_code": str}, encoding="cp949")
    return pd.read_excel(path, dtype={"plu_code": str})


# ══════════════════════════════════════════════
# ③ 전처리 + 유효 피처 자동 선택 (v2 핵심 개선)
# ══════════════════════════════════════════════

def preprocess(
    df: pd.DataFrame,
    category_encoder: Optional[LabelEncoder] = None,
    fit_encoder: bool = True,
    active_features: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, LabelEncoder, List[str]]:
    """
    전처리 + 유효 피처 자동 선택.

    [v2 개선] 분산이 0인 피처 자동 제외.
    예시: 데이터가 1개 연도뿐이면 month 분산이 매우 작거나 0일 수 있음.
         academic_event, building_headcount가 전부 0이면 자동 제외.

    Returns
    -------
    (처리된 DataFrame, LabelEncoder, 실제 사용 피처 목록)
    """
    df = df.copy()

    # 카테고리 컬럼 처리
    cat_col = "category_m" if "category_m" in df.columns else "category_l"
    if cat_col not in df.columns:
        df["category_m"] = "기타"
        cat_col = "category_m"

    df[cat_col] = df[cat_col].fillna("기타").astype(str).str.strip()
    df.loc[df[cat_col] == "", cat_col] = "기타"

    # 카테고리 인코딩
    if category_encoder is None:
        category_encoder = LabelEncoder()
    if fit_encoder:
        category_encoder.fit(df[cat_col])
    else:
        known = set(category_encoder.classes_)
        fallback = "기타" if "기타" in known else category_encoder.classes_[0]
        df.loc[~df[cat_col].isin(known), cat_col] = fallback

    df["category_encoded"] = category_encoder.transform(df[cat_col])

    # 수치형 피처 정리
    for col in CANDIDATE_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce").fillna(0).clip(lower=0)

    # ── 유효 피처 자동 선택 ──
    if active_features is not None:
        # 테스트 단계: 훈련 때 확정된 피처 목록 그대로 사용
        return df, category_encoder, active_features

    # 훈련 단계: 분산이 0인 피처 제외
    valid_features = []
    excluded = []
    for col in CANDIDATE_FEATURES:
        if col not in df.columns:
            excluded.append((col, "컬럼 없음"))
            continue
        variance = df[col].var()
        if variance == 0:
            excluded.append((col, f"분산=0 (값 전부 동일)"))
        else:
            valid_features.append(col)

    if excluded:
        print(f"  ⚠ 자동 제외된 피처 ({len(excluded)}개):")
        for col, reason in excluded:
            print(f"    - {col}: {reason}")

    print(f"  ✅ 학습에 사용할 피처 ({len(valid_features)}개): {valid_features}")
    return df, category_encoder, valid_features


# ══════════════════════════════════════════════
# ④ 시계열 분할
# ══════════════════════════════════════════════

def split_by_year(
    df: pd.DataFrame,
    train_years: List[int],
    test_years: List[int],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    연도 기준 Train/Test 분리.
    ⚠ 랜덤 분리 금지 — 시계열 데이터는 반드시 과거→미래 순서 유지.
    """
    train_df = df[df["date"].dt.year.isin(train_years)].copy()
    test_df  = df[df["date"].dt.year.isin(test_years)].copy()

    print(f"  훈련: {len(train_df):,}행 | {sorted(train_years)}년")
    if not test_df.empty:
        print(f"  테스트: {len(test_df):,}행 | {sorted(test_years)}년")

    if train_df.empty:
        raise ValueError(
            f"훈련 데이터 없음. {train_years}년 데이터를 features 파일에 추가하세요."
        )
    return train_df, test_df


# ══════════════════════════════════════════════
# ⑤ 모델 학습
# ══════════════════════════════════════════════

def train_model(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestRegressor:
    """
    Random Forest 모델 학습.

    Random Forest 동작 원리:
      100개의 결정 트리를 각각 다른 데이터 부분집합으로 학습
      → 예측 시 100개 트리 평균값 사용
      → 단일 트리보다 안정적이고 과적합에 강함
    """
    model = RandomForestRegressor(**RF_PARAMS)
    model.fit(X_train, y_train)
    return model


# ══════════════════════════════════════════════
# ⑥ 성능 평가
# ══════════════════════════════════════════════

def evaluate(
    model: RandomForestRegressor,
    X: np.ndarray,
    y: np.ndarray,
    label: str,
    feature_cols: List[str],
) -> Dict:
    """
    성능 평가 + 피처 중요도 출력.

    MAE  : 평균 절대 오차 — "평균 ±N개 틀렸다"
    RMSE : 큰 오차에 민감 — 극단적 오류 탐지
    MAPE : 퍼센트 오차 — 직관적 이해
    R²   : 설명력 — 1에 가까울수록 좋음
    """
    y_pred = np.clip(model.predict(X), 0, None)

    mae  = mean_absolute_error(y, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
    r2   = float(model.score(X, y))

    mask = y > 0
    mape = float(np.mean(np.abs((y[mask] - y_pred[mask]) / y[mask])) * 100) if mask.any() else float("nan")

    print(f"\n  [{label}]")
    print(f"  {'─'*42}")
    print(f"  MAE  (평균 오차)   : {mae:.2f} 개")
    print(f"  RMSE (제곱근 오차) : {rmse:.2f} 개")
    print(f"  MAPE (퍼센트 오차) : {mape:.1f} %")
    print(f"  R²   (설명력)      : {r2:.4f}  (1에 가까울수록 좋음)")

    importances = pd.Series(model.feature_importances_, index=feature_cols)
    top = importances.nlargest(min(10, len(feature_cols)))
    print(f"\n  [피처 중요도 Top {len(top)}]")
    for feat, imp in top.items():
        bar = "█" * int(imp * 50)
        print(f"  {feat:<24} {imp:.4f}  {bar}")

    return {
        "mae":       round(mae, 4),
        "rmse":      round(rmse, 4),
        "mape":      round(mape, 2),
        "r2":        round(r2, 4),
        "n_samples": int(len(y)),
    }


def cross_validate_timeseries(
    df: pd.DataFrame,
    feature_cols: List[str],
    n_splits: int = 3,
) -> Dict:
    """
    시계열 교차검증 (TimeSeriesSplit).
    테스트 데이터가 없을 때 과적합 여부 추정용.

    TimeSeriesSplit 동작:
      Fold 1: [1~3일] 훈련 → [4~5일] 테스트
      Fold 2: [1~7일] 훈련 → [8~9일] 테스트
      Fold 3: [1~11일] 훈련 → [12~15일] 테스트
      → 각 fold에서 미래 데이터로 테스트 (시간 순서 유지)
    """
    df_sorted = df.sort_values("date").reset_index(drop=True)
    X = df_sorted[feature_cols].values
    y = df_sorted[TARGET].values

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_maes = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        if len(train_idx) < 10:
            continue
        m = RandomForestRegressor(**RF_PARAMS)
        m.fit(X[train_idx], y[train_idx])
        preds = np.clip(m.predict(X[test_idx]), 0, None)
        mae = mean_absolute_error(y[test_idx], preds)
        fold_maes.append(mae)
        print(f"    Fold {fold}: MAE = {mae:.2f}")

    cv_mae = float(np.mean(fold_maes)) if fold_maes else float("nan")
    cv_std = float(np.std(fold_maes))  if fold_maes else float("nan")
    print(f"    평균 MAE: {cv_mae:.2f} ± {cv_std:.2f}")
    return {"cv_mae_mean": round(cv_mae, 4), "cv_mae_std": round(cv_std, 4)}


# ══════════════════════════════════════════════
# ⑦ 모델 저장
# ══════════════════════════════════════════════

def save_model(
    model: RandomForestRegressor,
    category_encoder: LabelEncoder,
    feature_cols: List[str],
    train_metrics: Dict,
    test_metrics: Optional[Dict],
    cv_metrics: Optional[Dict],
    train_years: List[int],
    test_years: List[int],
) -> str:
    """학습된 모델 + 메타 정보 저장."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    version      = f"rf_v2_{datetime.now().strftime('%Y%m%d_%H%M')}"
    latest_path  = MODEL_DIR / "rf_model_latest.joblib"
    backup_path  = MODEL_DIR / "rf_model_backup.joblib"
    enc_path     = MODEL_DIR / "category_encoder.joblib"
    meta_path    = MODEL_DIR / "model_meta.json"

    if latest_path.exists():
        shutil.copy(latest_path, backup_path)
        print(f"  기존 모델 백업: {backup_path}")

    joblib.dump(model,            latest_path)
    joblib.dump(category_encoder, enc_path)

    meta = {
        "version":          version,
        "trained_at":       datetime.now().isoformat(),
        "train_years":      train_years,
        "test_years":       test_years,
        "feature_columns":  feature_cols,   # FastAPI가 동일 피처로 예측
        "rf_params":        RF_PARAMS,
        "category_classes": list(category_encoder.classes_),
        "train_metrics":    train_metrics,
        "test_metrics":     test_metrics,
        "cv_metrics":       cv_metrics,
        "model_path":       str(latest_path),
        "encoder_path":     str(enc_path),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 모델 저장   : {latest_path}")
    print(f"  💾 인코더 저장 : {enc_path}")
    print(f"  💾 메타 저장   : {meta_path}")
    print(f"  버전: {version}")
    return version


# ══════════════════════════════════════════════
# ⑧ 메인 파이프라인
# ══════════════════════════════════════════════

def run(
    data_dir: str = "data/processed",
    data_file: Optional[str] = None,
    train_years: Optional[List[int]] = None,
    test_years: Optional[List[int]] = None,
) -> Optional[str]:
    """메인 실행 함수 (터미널 / Colab 공용)."""
    print("=" * 62)
    print("  에러없조 | Random Forest 수요 예측 모델 학습기 v2")
    print("=" * 62)

    # Step 1: 데이터 로드
    print("\n[Step 1] 데이터 로드")
    data_path = data_file if data_file else data_dir
    try:
        df = load_features(data_path)
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
        return None

    # Step 2: 연도 자동 설정
    available = sorted(df["date"].dt.year.unique().tolist())
    print(f"  보유 연도: {available}")

    if train_years is None:
        if len(available) >= 2:
            train_years = available[:-1]
            test_years  = test_years or [available[-1]]
        else:
            train_years = available
            test_years  = []
            print("  ⚠ 단일 연도 → 전체 훈련 모드 (교차검증으로 성능 추정)")

    test_years = test_years or []
    print(f"  훈련: {train_years} | 테스트: {test_years if test_years else '없음'}")

    # Step 3: 전처리 + 유효 피처 선택
    print("\n[Step 2] 전처리 + 유효 피처 자동 선택")
    df_proc, enc, active_features = preprocess(df, fit_encoder=True)

    # Step 4: 시계열 분할
    print("\n[Step 3] 시계열 분할")
    if test_years:
        train_df, test_df = split_by_year(df_proc, train_years, test_years)
    else:
        train_df = df_proc.copy()
        test_df  = pd.DataFrame()

    X_train = train_df[active_features].values
    y_train = train_df[TARGET].values

    # Step 5: 모델 학습
    print("\n[Step 4] Random Forest 학습")
    print(f"  트리 {RF_PARAMS['n_estimators']}개 | 최대깊이 {RF_PARAMS['max_depth']} | 학습 중...")
    model = train_model(X_train, y_train)
    print("  ✅ 학습 완료")

    # Step 6: 성능 평가
    print("\n[Step 5] 성능 평가")
    train_metrics = evaluate(model, X_train, y_train, "훈련 데이터", active_features)

    test_metrics = None
    if not test_df.empty:
        test_proc, _, _ = preprocess(test_df, category_encoder=enc,
                                     fit_encoder=False, active_features=active_features)
        X_test = test_proc[active_features].values
        y_test = test_proc[TARGET].values
        test_metrics = evaluate(model, X_test, y_test,
                                f"테스트 데이터 ({test_years}년)", active_features)
    else:
        # 테스트 없을 때 교차검증으로 추정
        print("\n  [시계열 교차검증 — 테스트 데이터 대체 추정]")
        cv_metrics = cross_validate_timeseries(train_df, active_features)

    cv_metrics_val = cv_metrics if test_df.empty else None

    # Step 7: 모델 저장
    print("\n[Step 6] 모델 저장")
    version = save_model(
        model, enc, active_features,
        train_metrics, test_metrics, cv_metrics_val,
        train_years, test_years,
    )

    # 최종 요약
    print("\n" + "=" * 62)
    print("  ✅ 학습 완료")
    print("=" * 62)
    print(f"  모델 버전   : {version}")
    print(f"  사용 피처   : {len(active_features)}개")
    print(f"  훈련 MAE    : {train_metrics['mae']:.2f}개")

    if test_metrics:
        print(f"  테스트 MAE  : {test_metrics['mae']:.2f}개  ← 실제 운영 성능 기준")
        print(f"  테스트 R²   : {test_metrics['r2']:.4f}")
        ratio = train_metrics["mae"] / (test_metrics["mae"] + 1e-9)
        if ratio < 0.5:
            print(f"\n  ⚠ 과적합 가능성: 훈련 MAE가 테스트의 {ratio:.0%}")
            print(f"     데이터 누적 시 자연스럽게 해소됩니다.")
        else:
            print(f"\n  ✅ 과적합 없음 (훈련/테스트 균형적)")
    elif cv_metrics_val:
        print(f"  교차검증 MAE: {cv_metrics_val['cv_mae_mean']:.2f} ± {cv_metrics_val['cv_mae_std']:.2f}개")
        print(f"     (테스트 데이터 없을 때 추정치, 25년 데이터 추가 후 재확인 권장)")

    print(f"\n  저장 위치: saved_models/")
    print(f"  다음 단계: python main_v2.py")
    return version


# ══════════════════════════════════════════════
# ⑨ CLI
# ══════════════════════════════════════════════

def _is_interactive() -> bool:
    try:
        get_ipython()  # type: ignore  # noqa
        return True
    except NameError:
        return False


def main():
    if _is_interactive():
        print("Colab/Jupyter → run() 함수를 사용하세요.")
        print("from trainer_v2 import run")
        print("run(data_dir='data/processed', train_years=[2024], test_years=[2025])")
        return

    parser = argparse.ArgumentParser(
        description="에러없조 | RF 수요 예측 모델 학습기 v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python trainer_v2.py                                    # data/processed 자동 탐색
  python trainer_v2.py --data data/processed/sales.csv   # 파일 직접 지정
  python trainer_v2.py --train-years 2024 --test-years 2025
  python trainer_v2.py --train-years 2024 2025 --test-years 2026
        """
    )
    parser.add_argument("--data", default="data/processed",
                        help="features 파일 또는 폴더 경로")
    parser.add_argument("--train-years", type=int, nargs="+")
    parser.add_argument("--test-years",  type=int, nargs="+")
    args = parser.parse_args()

    p = Path(args.data)
    run(
        data_dir=str(p) if p.is_dir() else "data/processed",
        data_file=str(p) if p.is_file() else None,
        train_years=args.train_years,
        test_years=args.test_years,
    )


if __name__ == "__main__":
    main()
