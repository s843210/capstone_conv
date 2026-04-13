"""
trainer.py  ─  에러없조 | Random Forest 수요 예측 모델 학습기
=============================================================================
◎ 학습 전략 (시계열 분할)
  - 훈련(Train) : 24년 데이터  → 모델이 패턴을 학습
  - 테스트(Test): 25년 데이터  → 학습된 모델의 실제 성능 검증
  - 미래 예측   : 26년 이후    → 저장된 모델로 FastAPI에서 사용

  ⚠ 왜 날짜 기준으로 분리하나?
    시계열 데이터는 랜덤 분리(train_test_split)하면 안 돼.
    미래 데이터로 과거를 예측하는 "미래 유출(Data Leakage)" 문제가 생김.
    반드시 과거 → 미래 순서로 분리해야 실제 운영 성능과 일치함.

◎ 피처 구성 (현재 Phase 0 ~ 1)
  [판매 시계열] lag_1, lag_3, lag_7, rolling_7_mean, rolling_7_std
  [캘린더]      day_of_week, month, is_holiday
  [카테고리]    category_m (원-핫 인코딩)
  [Phase 2+]   academic_event, building_headcount (데이터 확보 후 활성화)

◎ 출력
  saved_models/rf_model_latest.joblib  ← FastAPI가 로드하는 모델
  saved_models/rf_model_backup.joblib  ← 이전 버전 백업
  saved_models/model_meta.json         ← 버전/피처 정보

◎ 사용법
  [터미널/VSCode]
    # 기본 실행 (data/processed 폴더 전체 자동 탐색)
    python trainer.py

    # 파일 직접 지정
    python trainer.py --data data/processed/sales_2024_features.csv

    # 훈련/테스트 연도 지정
    python trainer.py --train-years 2024 --test-years 2025

  [Google Colab]
    from trainer import run
    result = run(data_dir='data/processed', train_years=[2024], test_years=[2025])
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
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════
# ① 상수 및 설정
# ══════════════════════════════════════════════

# RF 모델 저장 경로
MODEL_DIR = Path("saved_models")

# 현재 사용하는 피처 목록 (Phase 0~1 기준)
# Phase 2에서 academic_event, building_headcount 추가 예정
BASE_FEATURES = [
    "lag_1",            # 어제 판매량
    "lag_3",            # 3일 전 판매량
    "lag_7",            # 7일 전 판매량 (동일 요일)
    "rolling_7_mean",   # 최근 7일 평균
    "rolling_7_std",    # 최근 7일 변동성
    "day_of_week",      # 요일 (월=0, 일=6)
    "month",            # 월 (1~12)
    "is_holiday",       # 공휴일/주말 여부
    "safety_stock",     # 카테고리별 안전재고 기준값
]

# 카테고리 피처 (원-핫 인코딩 적용)
CATEGORY_FEATURE = "category_m"

# 타겟 컬럼
TARGET = "sales"

# RF 하이퍼파라미터 (Phase 0~1 기준, 데이터 많아지면 조정)
RF_PARAMS = {
    "n_estimators": 100,       # 트리 개수: 많을수록 안정적이나 느림
    "max_depth": 10,           # 트리 깊이 제한: 과적합 방지
    "min_samples_leaf": 3,     # 리프 노드 최소 샘플 수: 과적합 방지
    "max_features": "sqrt",    # 분기 시 고려할 피처 수: sqrt(n_features)
    "random_state": 42,        # 재현성 보장
    "n_jobs": -1,              # 모든 CPU 코어 활용
}


# ══════════════════════════════════════════════
# ② 데이터 로드
# ══════════════════════════════════════════════

def load_features(data_path: str) -> pd.DataFrame:
    """
    converter_v2.py가 만든 features CSV/XLSX 로드.
    여러 파일이 있으면 전부 합쳐서 하나의 DataFrame으로 반환.
    """
    path = Path(data_path)
    all_frames = []

    # 디렉토리면 안의 features 파일 전부 탐색
    if path.is_dir():
        csv_files  = sorted(path.glob("*features*.csv"))
        xlsx_files = sorted(path.glob("*features*.xlsx"))
        targets = csv_files if csv_files else xlsx_files

        if not targets:
            raise FileNotFoundError(
                f"'{data_path}' 폴더에 features 파일이 없습니다.\n"
                f"converter_v2.py를 먼저 실행해서 features.csv를 생성하세요."
            )

        print(f"  features 파일 {len(targets)}개 탐지:")
        for f in targets:
            print(f"    - {f.name}")
            df = _read_one_file(str(f))
            all_frames.append(df)

    # 단일 파일
    elif path.exists():
        print(f"  파일 로드: {path.name}")
        all_frames.append(_read_one_file(str(path)))
    else:
        raise FileNotFoundError(f"파일/폴더를 찾을 수 없습니다: {data_path}")

    combined = pd.concat(all_frames, ignore_index=True)

    # 날짜 파싱
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    combined = combined.dropna(subset=["date"])

    # 중복 제거 (같은 날짜+PLU가 여러 파일에 있을 경우)
    key_col = "plu_code" if "plu_code" in combined.columns else "product_name"
    combined = (
        combined
        .sort_values("date")
        .drop_duplicates(subset=["date", key_col], keep="last")
        .reset_index(drop=True)
    )

    # plu_code 빈칸 처리
    if "plu_code" in combined.columns:
        combined["plu_code"] = combined["plu_code"].fillna("").astype(str).str.strip()

    print(f"  ✅ 총 {len(combined):,}행 로드 | "
          f"{combined['date'].dt.year.unique().tolist()} 연도 포함 | "
          f"{combined[key_col].nunique():,}개 상품")
    return combined


def _read_one_file(path: str) -> pd.DataFrame:
    """CSV 또는 XLSX 파일 1개 읽기."""
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        try:
            return pd.read_csv(path, dtype={"plu_code": str}, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, dtype={"plu_code": str}, encoding="cp949")
    else:
        return pd.read_excel(path, dtype={"plu_code": str})


# ══════════════════════════════════════════════
# ③ 전처리 (피처 엔지니어링)
# ══════════════════════════════════════════════

def preprocess(
    df: pd.DataFrame,
    category_encoder: Optional[LabelEncoder] = None,
    fit_encoder: bool = True,
) -> Tuple[pd.DataFrame, LabelEncoder]:
    """
    학습 전 데이터 전처리.

    1. category_m 라벨 인코딩 (문자 → 숫자)
       예: '음료' → 3, '과자' → 1
    2. 피처 컬럼 타입 정리
    3. 결측치 처리

    Parameters
    ----------
    df              : features DataFrame
    category_encoder: 기존에 fit된 LabelEncoder (테스트 시 재사용)
    fit_encoder     : True면 새로 fit, False면 기존 encoder 사용

    Returns
    -------
    (처리된 DataFrame, LabelEncoder)
    """
    df = df.copy()

    # category_m 없으면 빈칸으로 채움
    if CATEGORY_FEATURE not in df.columns:
        df[CATEGORY_FEATURE] = "기타"
    df[CATEGORY_FEATURE] = df[CATEGORY_FEATURE].fillna("기타").astype(str).str.strip()
    df.loc[df[CATEGORY_FEATURE] == "", CATEGORY_FEATURE] = "기타"

    # 카테고리 인코딩
    if category_encoder is None:
        category_encoder = LabelEncoder()

    if fit_encoder:
        # 훈련 데이터로 fit: 모든 카테고리를 숫자로 매핑
        category_encoder.fit(df[CATEGORY_FEATURE])
    else:
        # 테스트 데이터: 훈련 때 못 본 카테고리 → '기타'로 대체
        known_cats = set(category_encoder.classes_)
        df.loc[~df[CATEGORY_FEATURE].isin(known_cats), CATEGORY_FEATURE] = "기타"
        if "기타" not in known_cats:
            # 기타도 없으면 첫 번째 클래스로 대체
            df.loc[df[CATEGORY_FEATURE] == "기타", CATEGORY_FEATURE] = category_encoder.classes_[0]

    df["category_encoded"] = category_encoder.transform(df[CATEGORY_FEATURE])

    # 수치형 피처 타입 보장
    for col in BASE_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            # 피처가 없으면 0으로 채움 (Phase 0에서 academic_event 등)
            df[col] = 0

    # 타겟 컬럼
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce").fillna(0).clip(lower=0)

    return df, category_encoder


def get_feature_columns() -> List[str]:
    """
    실제 모델에 들어가는 최종 피처 컬럼 목록 반환.
    BASE_FEATURES + category_encoded
    """
    return BASE_FEATURES + ["category_encoded"]


# ══════════════════════════════════════════════
# ④ 시계열 분할 (핵심!)
# ══════════════════════════════════════════════

def split_by_year(
    df: pd.DataFrame,
    train_years: List[int],
    test_years: List[int],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    연도 기준 Train/Test 분리.

    ⚠ 왜 랜덤 분리(train_test_split)를 안 쓰나?
      판매 예측은 "과거로 미래를 예측"하는 문제.
      랜덤 분리하면 25년 데이터로 24년을 예측하는 상황이 생겨서
      실제 운영 성능보다 훨씬 좋은 수치가 나옴 → 의미 없는 평가.
      반드시 시간 순서를 지켜야 함.

    Parameters
    ----------
    train_years : 훈련에 사용할 연도 목록  예: [2024]
    test_years  : 테스트에 사용할 연도 목록 예: [2025]
    """
    train_mask = df["date"].dt.year.isin(train_years)
    test_mask  = df["date"].dt.year.isin(test_years)

    train_df = df[train_mask].copy()
    test_df  = df[test_mask].copy()

    print(f"  훈련 데이터: {len(train_df):,}행 | {train_years}년")
    print(f"  테스트 데이터: {len(test_df):,}행 | {test_years}년")

    if train_df.empty:
        raise ValueError(
            f"훈련 데이터가 없습니다. {train_years}년 데이터를 features 파일에 추가하세요."
        )

    return train_df, test_df


# ══════════════════════════════════════════════
# ⑤ 모델 학습
# ══════════════════════════════════════════════

def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> RandomForestRegressor:
    """
    Random Forest 모델 학습.

    Random Forest 동작 원리:
      1. 훈련 데이터에서 랜덤하게 샘플을 뽑아 여러 개의 결정 트리를 만듦
      2. 각 트리는 서로 다른 데이터 부분집합과 피처 조합을 봄
      3. 예측 시 모든 트리의 평균값을 최종 예측값으로 사용
      → 단일 트리보다 훨씬 안정적이고 과적합에 강함
    """
    model = RandomForestRegressor(**RF_PARAMS)
    # .values로 numpy 배열 변환 → 피처명 경고 방지
    model.fit(X_train.values, y_train.values)
    return model


# ══════════════════════════════════════════════
# ⑥ 성능 평가
# ══════════════════════════════════════════════

def evaluate(
    model: RandomForestRegressor,
    X: pd.DataFrame,
    y: pd.Series,
    label: str,
    feature_cols: List[str],
) -> Dict:
    """
    모델 성능 평가 및 출력.

    평가 지표 설명:
      MAE  (Mean Absolute Error)   : 평균 절대 오차. "평균적으로 ±N개 틀렸다"
      RMSE (Root Mean Squared Error): 큰 오차에 더 민감한 지표
      MAPE (Mean Abs Percentage Err): 퍼센트 기준 오차. 직관적으로 이해하기 쉬움
      R²   (결정계수)               : 1에 가까울수록 모델이 데이터를 잘 설명함
    """
    y_pred = model.predict(X)
    y_pred = np.clip(y_pred, 0, None)  # 음수 예측 방지

    mae  = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2   = model.score(X, y)

    # MAPE: 실제값이 0인 경우 제외하고 계산
    mask = y > 0
    mape = np.mean(np.abs((y[mask] - y_pred[mask]) / y[mask])) * 100 if mask.any() else float("nan")

    print(f"\n  [{label}] 성능 평가")
    print(f"  {'─'*40}")
    print(f"  MAE  (평균 오차)     : {mae:.2f} 개")
    print(f"  RMSE (제곱근 오차)   : {rmse:.2f} 개")
    print(f"  MAPE (퍼센트 오차)   : {mape:.1f} %")
    print(f"  R²   (설명력)        : {r2:.4f}  (1에 가까울수록 좋음)")

    # 피처 중요도 상위 10개
    importances = pd.Series(model.feature_importances_, index=feature_cols)
    top = importances.nlargest(10)
    print(f"\n  [피처 중요도 Top 10]")
    for feat, imp in top.items():
        bar = "█" * int(imp * 50)
        print(f"  {feat:<22} {imp:.4f}  {bar}")

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 2),
        "r2": round(r2, 4),
        "n_samples": int(len(y)),
    }


# ══════════════════════════════════════════════
# ⑦ 모델 저장
# ══════════════════════════════════════════════

def save_model(
    model: RandomForestRegressor,
    category_encoder: LabelEncoder,
    feature_cols: List[str],
    train_metrics: Dict,
    test_metrics: Optional[Dict],
    train_years: List[int],
    test_years: List[int],
) -> str:
    """
    학습된 모델과 메타 정보 저장.

    저장 파일:
      saved_models/rf_model_latest.joblib  ← FastAPI가 로드
      saved_models/rf_model_backup.joblib  ← 이전 버전 백업
      saved_models/category_encoder.joblib ← 카테고리 인코더
      saved_models/model_meta.json         ← 버전/피처/성능 정보
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 버전 문자열 생성 (날짜 기반)
    version = f"rf_v1_{datetime.now().strftime('%Y%m%d_%H%M')}"

    latest_path  = MODEL_DIR / "rf_model_latest.joblib"
    backup_path  = MODEL_DIR / "rf_model_backup.joblib"
    encoder_path = MODEL_DIR / "category_encoder.joblib"
    meta_path    = MODEL_DIR / "model_meta.json"

    # 기존 모델 → 백업
    if latest_path.exists():
        shutil.copy(latest_path, backup_path)
        print(f"  기존 모델 백업: {backup_path}")

    # 모델 + 인코더 저장
    joblib.dump(model,            latest_path)
    joblib.dump(category_encoder, encoder_path)

    # 메타 정보 저장 (FastAPI가 읽어서 /model/info 응답에 활용)
    meta = {
        "version":         version,
        "trained_at":      datetime.now().isoformat(),
        "train_years":     train_years,
        "test_years":      test_years,
        "feature_columns": feature_cols,
        "rf_params":       RF_PARAMS,
        "category_classes": list(category_encoder.classes_),
        "train_metrics":   train_metrics,
        "test_metrics":    test_metrics,
        "model_path":      str(latest_path),
        "encoder_path":    str(encoder_path),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 모델 저장: {latest_path}")
    print(f"  💾 인코더 저장: {encoder_path}")
    print(f"  💾 메타 저장: {meta_path}")
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
    """
    메인 실행 함수 (터미널 / Colab 공용).

    Parameters
    ----------
    data_dir    : features 파일이 있는 폴더 (data_file 없을 때 사용)
    data_file   : 특정 features 파일 직접 지정
    train_years : 훈련 연도 목록  예: [2024]      기본: 전체에서 가장 오래된 연도
    test_years  : 테스트 연도 목록 예: [2025]     기본: 가장 최근 연도
    """
    print("=" * 62)
    print("  에러없조 | Random Forest 수요 예측 모델 학습기")
    print("=" * 62)

    # ── Step 1: 데이터 로드 ──
    print("\n[Step 1] 데이터 로드")
    data_path = data_file if data_file else data_dir
    try:
        df = load_features(data_path)
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
        return None

    # ── Step 2: 연도 자동 설정 ──
    available_years = sorted(df["date"].dt.year.unique().tolist())
    print(f"  보유 데이터 연도: {available_years}")

    if train_years is None:
        # 기본: 가장 최근 연도 제외한 모든 연도 = 훈련
        if len(available_years) >= 2:
            train_years = available_years[:-1]
            test_years  = test_years or [available_years[-1]]
        else:
            # 연도가 1개뿐이면 80% 훈련, 20% 테스트 (날짜 기준)
            train_years = available_years
            test_years  = []
            print("  ⚠ 데이터가 1개 연도뿐입니다. 전체를 훈련 데이터로 사용합니다.")

    if test_years is None:
        test_years = []

    print(f"  훈련 연도: {train_years}")
    print(f"  테스트 연도: {test_years if test_years else '없음 (전체 훈련)'}")

    # ── Step 3: 전처리 ──
    print("\n[Step 2] 데이터 전처리")
    df_processed, category_encoder = preprocess(df, fit_encoder=True)
    feature_cols = get_feature_columns()
    print(f"  사용 피처 ({len(feature_cols)}개): {feature_cols}")
    print(f"  카테고리 종류: {len(category_encoder.classes_)}개")

    # ── Step 4: 시계열 분할 ──
    print("\n[Step 3] 시계열 분할 (연도 기준)")
    if test_years:
        train_df, test_df = split_by_year(df_processed, train_years, test_years)
    else:
        train_df = df_processed.copy()
        test_df  = pd.DataFrame()

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET]

    # ── Step 5: 모델 학습 ──
    print("\n[Step 4] Random Forest 학습")
    print(f"  트리 개수: {RF_PARAMS['n_estimators']}개")
    print(f"  최대 깊이: {RF_PARAMS['max_depth']}")
    print("  학습 중...")

    model = train_model(X_train, y_train)
    print("  ✅ 학습 완료!")

    # ── Step 6: 성능 평가 ──
    print("\n[Step 5] 성능 평가")
    train_metrics = evaluate(model, X_train, y_train, "훈련 데이터", feature_cols)

    test_metrics = None
    if not test_df.empty:
        # 테스트 데이터: 훈련 때 만든 encoder 재사용 (fit_encoder=False)
        test_df_proc, _ = preprocess(test_df, category_encoder=category_encoder, fit_encoder=False)
        X_test = test_df_proc[feature_cols]
        y_test = test_df_proc[TARGET]
        test_metrics = evaluate(model, X_test, y_test, "테스트 데이터 (25년)", feature_cols)
    else:
        print("\n  ℹ 테스트 데이터 없음 (단일 연도 학습 모드)")

    # ── Step 7: 모델 저장 ──
    print("\n[Step 6] 모델 저장")
    version = save_model(
        model, category_encoder, feature_cols,
        train_metrics, test_metrics,
        train_years, test_years,
    )

    # ── 최종 요약 ──
    print("\n" + "=" * 62)
    print("  ✅ 학습 완료 요약")
    print("=" * 62)
    print(f"  모델 버전     : {version}")
    print(f"  훈련 MAE      : {train_metrics['mae']:.2f} 개 (평균 오차)")
    if test_metrics:
        print(f"  테스트 MAE    : {test_metrics['mae']:.2f} 개 ← 실제 운영 성능 기준")
        print(f"  테스트 R²     : {test_metrics['r2']:.4f}")

        # 과적합 여부 간단 판단
        overfit_ratio = train_metrics["mae"] / (test_metrics["mae"] + 1e-9)
        if overfit_ratio < 0.5:
            print(f"\n  ⚠ 과적합 주의: 훈련 MAE가 테스트의 {overfit_ratio:.0%}.")
            print(f"     데이터가 더 쌓이면 자연스럽게 해소됩니다.")
        else:
            print(f"\n  ✅ 과적합 없음: 훈련/테스트 성능 균형적")

    print(f"\n  저장 위치: saved_models/")
    print(f"  다음 단계: python main.py  (FastAPI 서버 실행)")

    return version


# ══════════════════════════════════════════════
# ⑨ CLI 진입점
# ══════════════════════════════════════════════

def _is_interactive() -> bool:
    try:
        shell = get_ipython().__class__.__name__  # type: ignore  # noqa
        return True
    except NameError:
        return False


def main():
    if _is_interactive():
        print("Colab/Jupyter 환경입니다. run() 함수를 사용하세요.")
        print("from trainer import run")
        print("run(data_dir='data/processed', train_years=[2024], test_years=[2025])")
        return

    parser = argparse.ArgumentParser(
        description="에러없조 | RF 수요 예측 모델 학습기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 실행 (data/processed 자동 탐색)
  python trainer.py

  # 특정 파일 지정
  python trainer.py --data data/processed/sales_2024_features.csv

  # 훈련/테스트 연도 명시
  python trainer.py --train-years 2024 --test-years 2025

  # 여러 연도 훈련
  python trainer.py --train-years 2024 2025 --test-years 2026
        """
    )
    parser.add_argument("--data",        default="data/processed",
                        help="features 파일 또는 폴더 경로 (기본: data/processed)")
    parser.add_argument("--train-years", type=int, nargs="+",
                        help="훈련 연도 예: --train-years 2024")
    parser.add_argument("--test-years",  type=int, nargs="+",
                        help="테스트 연도 예: --test-years 2025")
    args = parser.parse_args()

    run(
        data_dir=args.data if Path(args.data).is_dir() else "data/processed",
        data_file=args.data if Path(args.data).is_file() else None,
        train_years=args.train_years,
        test_years=args.test_years,
    )


if __name__ == "__main__":
    main()
