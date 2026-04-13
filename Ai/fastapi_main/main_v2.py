"""
main_v2.py  ─  에러없조 | FastAPI AI 예측 서버
=============================================================================
[v1 → v2 개선 사항]
  1. @app.on_event deprecated 제거 → lifespan 방식으로 교체
  2. 공휴일 판단 강화 — 하드코딩 공휴일 목록 포함 (주말만 체크하던 문제 해결)
  3. 피처 컬럼을 model_meta.json에서 동적으로 로드
     → trainer_v2가 제외한 피처(month 등)와 자동으로 일치
  4. Optional 필드 null/빈값 처리 명확화
  5. 전체 주석 및 로그 가독성 개선

[엔드포인트 목록]
  GET  /health                 서버 상태 확인 (Spring Boot 헬스체크)
  POST /api/v1/predict         단일 상품 예측
  POST /api/v1/predict/batch   배치 예측 (전 상품, 매일 18:00)
  POST /api/v1/retrain         모델 재학습 트리거 (백그라운드)
  GET  /api/v1/model/info      현재 모델 정보 조회

[실행 방법]
  pip install fastapi uvicorn joblib scikit-learn
  python main_v2.py
  → http://localhost:8000/docs 에서 API 테스트
=============================================================================
"""

import json
import subprocess
import sys
import warnings
from contextlib import asynccontextmanager
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════
# ① 경로 설정
# ══════════════════════════════════════════════

MODEL_DIR   = Path("saved_models")
MODEL_PATH  = MODEL_DIR / "rf_model_latest.joblib"
BACKUP_PATH = MODEL_DIR / "rf_model_backup.joblib"
ENC_PATH    = MODEL_DIR / "category_encoder.joblib"
META_PATH   = MODEL_DIR / "model_meta.json"

STORE_ID = "chosun_emart24_01"  # 단일 매장 고정값

# 공휴일 목록 (converter_v3와 동일하게 유지)
KR_HOLIDAYS = {
    2024: [
        "2024-01-01","2024-02-09","2024-02-10","2024-02-11","2024-02-12",
        "2024-03-01","2024-04-10","2024-05-05","2024-05-06","2024-05-15",
        "2024-06-06","2024-08-15","2024-09-16","2024-09-17","2024-09-18",
        "2024-10-01","2024-10-03","2024-10-09","2024-12-25",
    ],
    2025: [
        "2025-01-01","2025-01-27","2025-01-28","2025-01-29","2025-01-30",
        "2025-03-01","2025-03-03","2025-05-05","2025-05-06","2025-06-03",
        "2025-06-06","2025-08-15","2025-10-03","2025-10-05","2025-10-06",
        "2025-10-07","2025-10-08","2025-10-09","2025-12-25",
    ],
    2026: [
        "2026-01-01","2026-02-16","2026-02-17","2026-02-18",
        "2026-03-01","2026-03-02","2026-05-05","2026-05-24","2026-05-25",
        "2026-06-03","2026-06-06","2026-07-17","2026-08-15","2026-08-17",
        "2026-09-24","2026-09-25","2026-09-26",
        "2026-10-03","2026-10-05","2026-10-09","2026-12-25",
    ],
}


def _build_holiday_set() -> set:
    """공휴일 날짜 집합 생성. holidays 라이브러리 있으면 우선 사용."""
    try:
        import holidays as holidays_lib
        years = list(range(2024, 2030))
        kr = holidays_lib.KR(years=years)
        return {pd.Timestamp(d).strftime("%Y-%m-%d") for d in kr.keys()}
    except Exception:
        pass
    result = set()
    for dates in KR_HOLIDAYS.values():
        result.update(dates)
    return result


HOLIDAY_SET: set = _build_holiday_set()


def is_holiday_or_weekend(date_str: str) -> int:
    """
    공휴일 또는 주말이면 1 반환.
    [v2 개선] 주말만 체크하던 v1에서 실제 공휴일 목록 포함으로 강화.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.weekday() >= 5:
            return 1
        if date_str in HOLIDAY_SET:
            return 1
        return 0
    except ValueError:
        return 0


# ══════════════════════════════════════════════
# ② 모델 저장소 (싱글톤)
# ══════════════════════════════════════════════

class ModelStore:
    """
    앱 시작 시 모델을 메모리에 올려두는 클래스.
    매 요청마다 파일을 읽으면 느리므로 메모리 상주.
    """
    def __init__(self):
        self.model           = None
        self.encoder         = None
        self.meta: dict      = {}
        self.feature_columns: List[str] = []
        self.is_loaded       = False
        self.is_retraining   = False

    def load(self) -> bool:
        try:
            if not MODEL_PATH.exists():
                print(f"  ⚠ 모델 없음: {MODEL_PATH}")
                print(f"    trainer_v2.py를 먼저 실행하세요.")
                return False

            self.model   = joblib.load(MODEL_PATH)
            self.encoder = joblib.load(ENC_PATH) if ENC_PATH.exists() else None

            if META_PATH.exists():
                with open(META_PATH, encoding="utf-8") as f:
                    self.meta = json.load(f)
                # [v2 개선] trainer_v2가 저장한 실제 사용 피처 목록 로드
                self.feature_columns = self.meta.get("feature_columns", [])

            self.is_loaded = True
            print(f"  ✅ 모델 로드: {self.meta.get('version','?')}")
            print(f"     피처 {len(self.feature_columns)}개: {self.feature_columns}")
            return True

        except Exception as e:
            print(f"  ❌ 모델 로드 실패: {e}")
            if BACKUP_PATH.exists():
                try:
                    self.model     = joblib.load(BACKUP_PATH)
                    self.is_loaded = True
                    print("  ↩ 백업 모델로 폴백 성공")
                    return True
                except Exception:
                    pass
            return False

    def reload(self) -> bool:
        self.is_loaded = False
        return self.load()


model_store = ModelStore()


# ══════════════════════════════════════════════
# ③ 안전재고 + 발주량 계산
# ══════════════════════════════════════════════

SAFETY_MULTIPLIERS = [
    ("담배",   1.0),
    ("음료",   0.5), ("과자",   0.5), ("캔디",   0.5),
    ("초콜릿", 0.5), ("초콜렛", 0.5), ("젤리",   0.5),
    ("유제품", 0.5), ("커피",   0.5), ("생수",   0.5),
    ("도시락", 0.3), ("김밥",   0.3), ("삼각",   0.3),
    ("밥류",   0.3), ("빵",     0.3), ("샌드위치", 0.3),
]


def get_safety_stock(category: str, rolling_7_mean: float) -> int:
    mult = 0.3
    for kw, m in SAFETY_MULTIPLIERS:
        if kw in str(category):
            mult = m
            break
    return max(0, round(rolling_7_mean * mult))


def calc_recommended_order(
    predicted_sales: float,
    safety_stock: int,
    current_stock: int,
    expected_inbound: int = 0,
) -> int:
    """
    발주 계산식 (규격서 v3 §1-4):
      max(0, ceil(predicted_sales) + safety_stock - current_stock - expected_inbound)
    """
    return max(0, ceil(predicted_sales) + safety_stock - current_stock - expected_inbound)


def calc_confidence_score(model, X: np.ndarray, history_days: int) -> float:
    """
    신뢰도 = 트리 간 일치도 × 데이터 충분도.
    트리가 서로 비슷한 값을 예측할수록 신뢰도 높음.
    """
    try:
        tree_preds = np.array([t.predict(X)[0] for t in model.estimators_])
        pred_mean  = np.mean(tree_preds)
        pred_std   = np.std(tree_preds)
        cv         = pred_std / (pred_mean + 1e-9)
        data_score = min(1.0, history_days / 30.0)
        score      = round((1.0 - min(cv, 1.0)) * data_score, 2)
        if history_days < 3:
            score = min(score, 0.3)
        return float(score)
    except Exception:
        return 0.3


# ══════════════════════════════════════════════
# ④ Pydantic 스키마
# ══════════════════════════════════════════════

class PredictRequest(BaseModel):
    """단일 상품 예측 요청."""
    plu_code:         str   = Field(..., description="PLU 풀코드 (Spring Boot에서 String 보장)")
    target_date:      str   = Field(..., description="예측 대상 날짜 YYYY-MM-DD")
    current_stock:    int   = Field(..., ge=0, description="현재 재고 수량")
    # 판매 이력 피처 (Spring Boot → DB 조회 후 전달, Phase 0에선 0으로 전달 가능)
    lag_1:            float = Field(0.0, description="어제 판매량")
    lag_3:            float = Field(0.0, description="3일 전 판매량")
    lag_7:            float = Field(0.0, description="7일 전 판매량")
    rolling_7_mean:   float = Field(0.0, description="최근 7일 평균 판매량")
    rolling_7_std:    float = Field(0.0, description="최근 7일 표준편차")
    category_m:       str   = Field("기타", description="중분류 카테고리")
    # 캘린더 — target_date로 자동 계산, 오버라이드 가능
    day_of_week:      Optional[int]   = Field(None, description="요일 (자동계산)")
    month:            Optional[int]   = Field(None, description="월 (자동계산)")
    is_holiday:       Optional[int]   = Field(None, description="공휴일 여부 (자동계산)")
    safety_stock:     Optional[float] = Field(None, description="안전재고 (자동계산)")
    academic_event:   Optional[int]   = Field(0,    description="학사 이벤트 (Phase 2)")
    building_headcount: Optional[int] = Field(0,    description="건물 수강인원 (Phase 2)")
    # 기타
    history_days:     int = Field(7, description="이 상품의 판매 이력 일수")
    expected_inbound: int = Field(0, description="이미 발주된 미입고 예정 수량")

    @field_validator("plu_code")
    @classmethod
    def plu_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("plu_code는 비어 있을 수 없습니다.")
        return v.strip()

    @field_validator("target_date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("target_date는 YYYY-MM-DD 형식이어야 합니다.")
        return v


class PredictResult(BaseModel):
    plu_code:          str
    target_date:       str
    predicted_sales:   float
    recommended_order: int
    confidence_score:  float
    safety_stock:      int
    model_version:     str
    predicted_at:      str


class BatchPredictRequest(BaseModel):
    items: List[PredictRequest] = Field(..., min_length=1, max_length=5000)


# ══════════════════════════════════════════════
# ⑤ FastAPI 앱 생성 (lifespan 방식)
# ══════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    [v2 개선] @app.on_event deprecated 제거 → lifespan 방식.
    FastAPI 0.93+ 권장 방식.
    """
    # 서버 시작 시
    print("\n" + "=" * 50)
    print("  에러없조 AI 서버 시작 (v2)")
    print("=" * 50)
    model_store.load()
    print(f"  서버: http://localhost:8000")
    print(f"  문서: http://localhost:8000/docs")
    print("=" * 50 + "\n")
    yield
    # 서버 종료 시 (필요하면 정리 작업)


app = FastAPI(
    title="에러없조 | 수요 예측 AI 서버 v2",
    description=(
        "이마트24 캠퍼스 편의점 수요 예측 및 발주 추천 API\n\n"
        "- 모델: Random Forest Regressor\n"
        "- 매일 18:00 Spring Boot → 배치 예측\n"
        "- trainer_v2.py 학습 모델 사용"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 시 Spring Boot 서버 IP로 제한
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════
# ⑥ 내부 예측 함수
# ══════════════════════════════════════════════

def _build_feature_row(req: PredictRequest) -> tuple:
    """
    PredictRequest → 모델 입력 numpy 배열 변환.

    [v2 개선] 피처 컬럼을 model_meta.json에서 동적으로 읽어서
              trainer_v2가 제외한 피처와 자동으로 일치.
    """
    dt = datetime.strptime(req.target_date, "%Y-%m-%d")

    # 캘린더 피처: 요청에 값 있으면 사용, 없으면 자동 계산
    day_of_week = req.day_of_week if req.day_of_week is not None else dt.weekday()
    month       = req.month       if req.month       is not None else dt.month
    is_holiday  = (req.is_holiday if req.is_holiday  is not None
                   else is_holiday_or_weekend(req.target_date))

    # 안전재고 자동 계산
    safety_stock = (
        req.safety_stock
        if req.safety_stock is not None
        else get_safety_stock(req.category_m, req.rolling_7_mean)
    )
    safety_stock = int(safety_stock)

    # 카테고리 인코딩
    category_encoded = 0
    if model_store.encoder is not None:
        cat = req.category_m or "기타"
        known = set(model_store.encoder.classes_)
        if cat not in known:
            cat = "기타" if "기타" in known else model_store.encoder.classes_[0]
        category_encoded = int(model_store.encoder.transform([cat])[0])

    # 전체 피처 딕셔너리
    all_features = {
        "lag_1":              req.lag_1,
        "lag_3":              req.lag_3,
        "lag_7":              req.lag_7,
        "rolling_7_mean":     req.rolling_7_mean,
        "rolling_7_std":      req.rolling_7_std,
        "day_of_week":        day_of_week,
        "month":              month,
        "is_holiday":         is_holiday,
        "safety_stock":       safety_stock,
        "academic_event":     req.academic_event or 0,
        "building_headcount": req.building_headcount or 0,
        "category_encoded":   category_encoded,
    }

    # [v2 핵심] trainer_v2가 실제 사용한 피처만 순서대로 추출
    feature_cols = model_store.feature_columns
    if not feature_cols:
        # 메타 없을 때 fallback
        feature_cols = [k for k in all_features if k != "month"]

    X = np.array([[all_features.get(col, 0) for col in feature_cols]])
    return X, safety_stock, feature_cols


def _predict_one(req: PredictRequest) -> PredictResult:
    """단일 상품 예측 내부 로직."""
    if not model_store.is_loaded:
        raise HTTPException(status_code=503, detail="MODEL_NOT_LOADED")
    if model_store.is_retraining:
        raise HTTPException(status_code=503, detail="MODEL_RETRAINING")

    X, safety_stock, _ = _build_feature_row(req)

    predicted_sales   = float(max(0.0, round(model_store.model.predict(X)[0], 1)))
    recommended_order = calc_recommended_order(
        predicted_sales, safety_stock, req.current_stock, req.expected_inbound
    )
    confidence        = calc_confidence_score(model_store.model, X, req.history_days)
    version           = model_store.meta.get("version", "rf_v2_unknown")

    return PredictResult(
        plu_code=req.plu_code,
        target_date=req.target_date,
        predicted_sales=predicted_sales,
        recommended_order=recommended_order,
        confidence_score=confidence,
        safety_stock=safety_stock,
        model_version=version,
        predicted_at=datetime.now().isoformat(),
    )


# ══════════════════════════════════════════════
# ⑦ API 엔드포인트
# ══════════════════════════════════════════════

@app.get("/health", tags=["운영"])
async def health_check():
    """서버 상태 확인 (Spring Boot 헬스체크)."""
    if not model_store.is_loaded:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "reason": "모델 미로드"}
        )
    return {
        "status":        "healthy",
        "model_version": model_store.meta.get("version", "?"),
        "is_retraining": model_store.is_retraining,
        "timestamp":     datetime.now().isoformat(),
        "store_id":      STORE_ID,
    }


@app.post("/api/v1/predict", response_model=PredictResult, tags=["예측"])
async def predict_single(req: PredictRequest):
    """
    단일 상품 예측.
    Spring Boot → 호출 → RF 예측 → 발주량 반환 → DB 저장.
    """
    try:
        return _predict_one(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PREDICTION_FAILED: {e}")


@app.post("/api/v1/predict/batch", tags=["예측"])
async def predict_batch(req: BatchPredictRequest):
    """
    배치 예측 (전 상품, 매일 18:00).
    개별 실패해도 나머지는 정상 반환.
    """
    results, failed = [], []
    t0 = datetime.now()

    for item in req.items:
        try:
            results.append(_predict_one(item))
        except Exception:
            failed.append(item.plu_code)

    elapsed_ms = int((datetime.now() - t0).total_seconds() * 1000)
    version    = model_store.meta.get("version", "?")

    return {
        "total_count":   len(req.items),
        "success_count": len(results),
        "fail_count":    len(failed),
        "results":       results,
        "failed_items":  failed,
        "batch_summary": {
            "total_recommended_order": sum(r.recommended_order for r in results),
            "low_confidence_items":    sum(1 for r in results if r.confidence_score < 0.5),
            "processing_ms":           elapsed_ms,
            "model_version":           version,
        },
    }


@app.get("/api/v1/model/info", tags=["모델"])
async def model_info():
    """현재 모델 정보 (대시보드용)."""
    if not model_store.is_loaded:
        raise HTTPException(status_code=503, detail="모델 미로드")
    return {
        "version":         model_store.meta.get("version", "?"),
        "trained_at":      model_store.meta.get("trained_at", ""),
        "train_years":     model_store.meta.get("train_years", []),
        "test_years":      model_store.meta.get("test_years", []),
        "feature_columns": model_store.feature_columns,
        "rf_params":       model_store.meta.get("rf_params", {}),
        "train_metrics":   model_store.meta.get("train_metrics", {}),
        "test_metrics":    model_store.meta.get("test_metrics"),
        "cv_metrics":      model_store.meta.get("cv_metrics"),
        "is_retraining":   model_store.is_retraining,
    }


def _retrain_bg():
    """재학습 백그라운드 실행."""
    model_store.is_retraining = True
    try:
        print("\n[재학습] trainer_v2.py 실행 중...")
        result = subprocess.run(
            [sys.executable, "trainer_v2.py"],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode == 0:
            model_store.reload()
            print("[재학습] 완료 — 새 모델 로드됨")
        else:
            print(f"[재학습] 실패:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("[재학습] 타임아웃 (600초)")
    except Exception as e:
        print(f"[재학습] 오류: {e}")
    finally:
        model_store.is_retraining = False


@app.post("/api/v1/retrain", tags=["모델"])
async def retrain(background_tasks: BackgroundTasks):
    """모델 재학습 트리거. 재학습 중에도 기존 모델로 서비스 유지."""
    if model_store.is_retraining:
        return {"status": "already_retraining", "message": "이미 재학습 진행 중"}
    background_tasks.add_task(_retrain_bg)
    return {
        "status":  "started",
        "message": "재학습이 백그라운드에서 시작되었습니다.",
        "note":    "재학습 중에도 기존 모델로 예측 서비스가 유지됩니다.",
    }


# ══════════════════════════════════════════════
# ⑧ 서버 실행
# ══════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(
        "main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
