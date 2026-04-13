"""
main.py  ─  에러없조 | FastAPI AI 예측 서버
=============================================================================
◎ 구조
  main.py              ← FastAPI 앱 + 서버 실행 진입점  (이 파일)
  schemas/             ← 요청/응답 데이터 형식 정의
  model/predictor.py   ← 예측 로직 (모델 로드 + 발주량 계산)

◎ 엔드포인트 목록 (규격서 v3 기준)
  GET  /health                  서버 상태 확인
  POST /api/v1/predict          단일 상품 예측
  POST /api/v1/predict/batch    배치 예측 (전 상품, 매일 18:00)
  POST /api/v1/retrain          모델 재학습 트리거
  GET  /api/v1/model/info       현재 모델 정보 조회

◎ 실행 방법
  [터미널/VSCode]
    pip install fastapi uvicorn
    python main.py

  [브라우저에서 API 문서 확인]
    http://localhost:8000/docs       ← Swagger UI (직접 테스트 가능)
    http://localhost:8000/redoc      ← ReDoc
=============================================================================
"""

import json
import subprocess
import sys
import threading
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ══════════════════════════════════════════════
# ① 경로 설정
# ══════════════════════════════════════════════

MODEL_DIR   = Path("saved_models")
MODEL_PATH  = MODEL_DIR / "rf_model_latest.joblib"
BACKUP_PATH = MODEL_DIR / "rf_model_backup.joblib"
ENC_PATH    = MODEL_DIR / "category_encoder.joblib"
META_PATH   = MODEL_DIR / "model_meta.json"

# 이 매장 고정값 (단일 매장 운영, Spring Boot에서도 동일하게 관리)
STORE_ID = "chosun_emart24_01"


# ══════════════════════════════════════════════
# ② 모델 로더 (싱글톤 패턴)
# ══════════════════════════════════════════════

class ModelStore:
    """
    FastAPI 앱 시작 시 모델을 딱 한 번만 메모리에 올려두는 클래스.
    매 요청마다 파일에서 읽으면 느리기 때문에 메모리에 상주시킴.
    """
    def __init__(self):
        self.model           = None   # RandomForestRegressor
        self.encoder         = None   # LabelEncoder (카테고리)
        self.meta            = {}     # model_meta.json 내용
        self.feature_columns = []     # 피처 컬럼 순서
        self.is_loaded       = False
        self.is_retraining   = False  # 재학습 중 여부

    def load(self) -> bool:
        """모델 파일 로드. 성공하면 True 반환."""
        try:
            if not MODEL_PATH.exists():
                print(f"  ⚠ 모델 파일 없음: {MODEL_PATH}")
                print(f"    먼저 trainer.py를 실행해서 모델을 학습시키세요.")
                return False

            self.model   = joblib.load(MODEL_PATH)
            self.encoder = joblib.load(ENC_PATH) if ENC_PATH.exists() else None

            if META_PATH.exists():
                with open(META_PATH, encoding="utf-8") as f:
                    self.meta = json.load(f)
                self.feature_columns = self.meta.get("feature_columns", [])

            self.is_loaded = True
            version = self.meta.get("version", "unknown")
            print(f"  ✅ 모델 로드 완료: {version}")
            return True

        except Exception as e:
            print(f"  ❌ 모델 로드 실패: {e}")
            # 백업 모델로 폴백 시도
            if BACKUP_PATH.exists():
                try:
                    self.model = joblib.load(BACKUP_PATH)
                    self.is_loaded = True
                    print(f"  ↩ 백업 모델로 폴백 성공")
                    return True
                except Exception:
                    pass
            return False

    def reload(self) -> bool:
        """재학습 후 새 모델 다시 로드."""
        self.is_loaded = False
        return self.load()


# 전역 모델 저장소 (앱 전체에서 공유)
model_store = ModelStore()


# ══════════════════════════════════════════════
# ③ 안전재고 + 발주량 계산
# ══════════════════════════════════════════════

SAFETY_MULTIPLIERS = {
    "담배": 1.0,
    "음료": 0.5, "과자": 0.5, "캔디": 0.5, "초콜릿": 0.5, "초콜렛": 0.5,
    "젤리": 0.5, "유제품": 0.5, "커피": 0.5, "생수": 0.5,
    "도시락": 0.3, "김밥": 0.3, "삼각": 0.3, "밥류": 0.3,
    "빵": 0.3, "샌드위치": 0.3,
}


def get_safety_stock(category: str, rolling_7_mean: float) -> int:
    """카테고리와 최근 7일 평균으로 안전재고 계산."""
    multiplier = 0.3  # 기본값
    for keyword, mult in SAFETY_MULTIPLIERS.items():
        if keyword in str(category):
            multiplier = mult
            break
    return max(0, round(rolling_7_mean * multiplier))


def calc_recommended_order(
    predicted_sales: float,
    safety_stock: int,
    current_stock: int,
    expected_inbound: int = 0,
) -> int:
    """
    발주 계산식 (규격서 v3 §1-4 기준):
      recommended_order = max(0, ceil(predicted_sales) + safety_stock
                              - current_stock - expected_inbound)

    풀이:
      내일 예상 판매량(ceil) + 안전재고 = 필요한 최소 재고
      거기서 현재 재고와 이미 발주된 물량 빼면 = 오늘 발주해야 할 양
    """
    needed = ceil(predicted_sales) + safety_stock
    order  = max(0, needed - current_stock - expected_inbound)
    return int(order)


def calc_confidence_score(model, X: pd.DataFrame, history_days: int) -> float:
    """
    예측 신뢰도 계산 (규격서 v3 §1-4 기준).
    - 트리 간 예측 일치도가 높을수록 신뢰도 높음
    - 데이터가 충분할수록 신뢰도 높음
    """
    try:
        # 각 트리의 예측값 수집
        tree_preds = np.array([
            tree.predict(X.values)[0]
            for tree in model.estimators_
        ])
        pred_mean = np.mean(tree_preds)
        pred_std  = np.std(tree_preds)

        # 변동계수 (낮을수록 트리들이 일치 → 신뢰도 높음)
        cv = pred_std / (pred_mean + 1e-9)

        # 데이터 충분도 (30일 이상이면 1.0)
        data_score = min(1.0, history_days / 30.0)

        score = round((1.0 - min(cv, 1.0)) * data_score, 2)

        # 신상품(이력 없음): 최대 0.3
        if history_days < 3:
            score = min(score, 0.3)

        return float(score)

    except Exception:
        return 0.3  # 계산 실패 시 낮은 신뢰도 반환


# ══════════════════════════════════════════════
# ④ Pydantic 스키마 (요청/응답 형식)
# ══════════════════════════════════════════════

class PredictRequest(BaseModel):
    """단일 상품 예측 요청"""
    plu_code:         str   = Field(..., description="PLU 풀코드 (Spring Boot에서 String 보장)")
    target_date:      str   = Field(..., description="예측 대상 날짜 YYYY-MM-DD")
    current_stock:    int   = Field(..., ge=0, description="현재 재고 수량")
    # 판매 이력 피처 (Spring Boot가 DB에서 조회해서 전달)
    lag_1:            float = Field(0.0,  description="어제 판매량")
    lag_3:            float = Field(0.0,  description="3일 전 판매량")
    lag_7:            float = Field(0.0,  description="7일 전 판매량")
    rolling_7_mean:   float = Field(0.0,  description="최근 7일 평균 판매량")
    rolling_7_std:    float = Field(0.0,  description="최근 7일 표준편차")
    category_m:       str   = Field("기타", description="중분류 카테고리")
    # 캘린더 (FastAPI가 target_date로 자동 계산, 전달값으로 오버라이드 가능)
    day_of_week:      Optional[int]   = Field(None, description="요일 (자동계산)")
    month:            Optional[int]   = Field(None, description="월 (자동계산)")
    is_holiday:       Optional[int]   = Field(None, description="공휴일 여부 (자동계산)")
    safety_stock:     Optional[float] = Field(None, description="안전재고 (자동계산)")
    # 추가 정보
    history_days:     int   = Field(7,   description="이 상품의 판매 이력 일수")
    expected_inbound: int   = Field(0,   description="이미 발주된 미입고 예정 수량")

    @field_validator("plu_code")
    @classmethod
    def plu_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("plu_code는 비어 있을 수 없습니다.")
        return v.strip()

    @field_validator("target_date")
    @classmethod
    def valid_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("target_date는 YYYY-MM-DD 형식이어야 합니다.")
        return v


class PredictResult(BaseModel):
    """단일 상품 예측 결과"""
    plu_code:          str
    target_date:       str
    predicted_sales:   float
    recommended_order: int
    confidence_score:  float
    safety_stock:      int
    model_version:     str
    predicted_at:      str


class BatchPredictRequest(BaseModel):
    """배치 예측 요청 (매일 18:00 전 상품)"""
    items: List[PredictRequest] = Field(..., min_length=1, max_length=5000)


class BatchPredictResponse(BaseModel):
    """배치 예측 결과"""
    total_count:   int
    success_count: int
    fail_count:    int
    results:       List[PredictResult]
    failed_items:  List[str]
    batch_summary: dict


class ErrorResponse(BaseModel):
    """에러 응답"""
    error_code:       str
    message:          str
    detail:           Optional[str] = None
    fallback_applied: bool = False


# ══════════════════════════════════════════════
# ⑤ FastAPI 앱 생성
# ══════════════════════════════════════════════

app = FastAPI(
    title="에러없조 | 수요 예측 AI 서버",
    description=(
        "이마트24 캠퍼스 편의점 수요 예측 및 발주 추천 API\n\n"
        "- 모델: Random Forest Regressor (scikit-learn)\n"
        "- 매일 18:00 Spring Boot → 이 서버로 배치 예측 요청\n"
        "- 규격서 v3 기준"
    ),
    version="1.0.0",
)

# CORS 설정 (Spring Boot와 통신 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 운영 시 Spring Boot 서버 IP로 제한
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════
# ⑥ 앱 시작/종료 이벤트
# ══════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 모델 자동 로드."""
    print("\n" + "=" * 50)
    print("  에러없조 AI 서버 시작")
    print("=" * 50)
    model_store.load()
    print(f"  서버 주소: http://localhost:8000")
    print(f"  API 문서:  http://localhost:8000/docs")
    print("=" * 50 + "\n")


# ══════════════════════════════════════════════
# ⑦ 내부 예측 함수
# ══════════════════════════════════════════════

def _build_feature_row(req: PredictRequest) -> pd.DataFrame:
    """
    PredictRequest → 모델 입력 피처 DataFrame 변환.
    target_date 기준으로 캘린더 피처 자동 계산.
    """
    dt = datetime.strptime(req.target_date, "%Y-%m-%d")

    # 캘린더 피처: 요청에 값이 있으면 사용, 없으면 자동 계산
    day_of_week = req.day_of_week if req.day_of_week is not None else dt.weekday()
    month       = req.month       if req.month       is not None else dt.month
    is_holiday  = req.is_holiday  if req.is_holiday  is not None else int(dt.weekday() >= 5)

    # 카테고리 인코딩
    category_encoded = 0
    if model_store.encoder is not None:
        cat = req.category_m if req.category_m else "기타"
        known_cats = set(model_store.encoder.classes_)
        if cat not in known_cats:
            cat = "기타" if "기타" in known_cats else model_store.encoder.classes_[0]
        category_encoded = int(model_store.encoder.transform([cat])[0])

    # 안전재고 자동 계산
    safety_stock = (
        req.safety_stock
        if req.safety_stock is not None
        else get_safety_stock(req.category_m, req.rolling_7_mean)
    )

    row = {
        "lag_1":            req.lag_1,
        "lag_3":            req.lag_3,
        "lag_7":            req.lag_7,
        "rolling_7_mean":   req.rolling_7_mean,
        "rolling_7_std":    req.rolling_7_std,
        "day_of_week":      day_of_week,
        "month":            month,
        "is_holiday":       is_holiday,
        "safety_stock":     safety_stock,
        "category_encoded": category_encoded,
    }

    # 모델이 기대하는 피처 순서 맞추기
    feature_cols = model_store.feature_columns if model_store.feature_columns else list(row.keys())
    return pd.DataFrame([row])[feature_cols], int(safety_stock)


def _predict_one(req: PredictRequest) -> PredictResult:
    """단일 상품 예측 내부 로직."""
    if not model_store.is_loaded:
        raise HTTPException(status_code=503, detail="MODEL_NOT_LOADED")

    if model_store.is_retraining:
        raise HTTPException(status_code=503, detail="MODEL_RETRAINING")

    X, safety_stock = _build_feature_row(req)

    # 예측 (numpy 배열로 변환해서 피처명 경고 방지)
    predicted_sales = float(model_store.model.predict(X.values)[0])
    predicted_sales = max(0.0, round(predicted_sales, 1))

    # 발주량 계산
    recommended_order = calc_recommended_order(
        predicted_sales,
        safety_stock,
        req.current_stock,
        req.expected_inbound,
    )

    # 신뢰도
    confidence = calc_confidence_score(model_store.model, X, req.history_days)

    version = model_store.meta.get("version", "rf_v1_unknown")

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
# ⑧ API 엔드포인트
# ══════════════════════════════════════════════

@app.get("/health", tags=["운영"])
async def health_check():
    """
    서버 상태 확인 (Spring Boot 헬스체크용).
    모델이 로드되어 있으면 200, 없으면 503 반환.
    """
    if not model_store.is_loaded:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "reason": "모델 미로드"}
        )
    return {
        "status":        "healthy",
        "model_version": model_store.meta.get("version", "unknown"),
        "is_retraining": model_store.is_retraining,
        "timestamp":     datetime.now().isoformat(),
        "store_id":      STORE_ID,
    }


@app.post("/api/v1/predict", response_model=PredictResult, tags=["예측"])
async def predict_single(req: PredictRequest):
    """
    단일 상품 예측.

    Spring Boot → 이 엔드포인트 호출 시 흐름:
      1. PLU코드 + 현재고 + 판매이력 피처 전달
      2. RF 모델로 내일 판매량 예측
      3. 발주량 계산 후 반환
      4. Spring Boot가 ai_prediction 테이블에 저장
    """
    try:
        return _predict_one(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PREDICTION_FAILED: {str(e)}"
        )


@app.post("/api/v1/predict/batch", tags=["예측"])
async def predict_batch(req: BatchPredictRequest):
    """
    배치 예측 (전 상품, 매일 18:00 자동 실행).

    Spring Boot에서 전체 상품 목록을 한 번에 전달하면
    모든 상품에 대해 예측 후 결과 반환.
    개별 상품 실패해도 나머지는 정상 반환.
    """
    results      = []
    failed_items = []
    start_time   = datetime.now()

    for item in req.items:
        try:
            result = _predict_one(item)
            results.append(result)
        except Exception as e:
            failed_items.append(item.plu_code)

    elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    # 배치 요약
    total_order       = sum(r.recommended_order for r in results)
    low_conf_count    = sum(1 for r in results if r.confidence_score < 0.5)
    version = model_store.meta.get("version", "unknown")

    return {
        "total_count":   len(req.items),
        "success_count": len(results),
        "fail_count":    len(failed_items),
        "results":       results,
        "failed_items":  failed_items,
        "batch_summary": {
            "total_recommended_order": total_order,
            "low_confidence_items":    low_conf_count,
            "processing_ms":           elapsed_ms,
            "model_version":           version,
        },
    }


@app.get("/api/v1/model/info", tags=["모델"])
async def model_info():
    """현재 로드된 모델 정보 반환 (대시보드용)."""
    if not model_store.is_loaded:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")

    return {
        "version":         model_store.meta.get("version", "unknown"),
        "trained_at":      model_store.meta.get("trained_at", ""),
        "train_years":     model_store.meta.get("train_years", []),
        "test_years":      model_store.meta.get("test_years", []),
        "feature_columns": model_store.feature_columns,
        "rf_params":       model_store.meta.get("rf_params", {}),
        "train_metrics":   model_store.meta.get("train_metrics", {}),
        "test_metrics":    model_store.meta.get("test_metrics", {}),
        "is_retraining":   model_store.is_retraining,
        "model_path":      str(MODEL_PATH),
    }


def _retrain_background():
    """재학습 백그라운드 실행 함수."""
    model_store.is_retraining = True
    try:
        print("\n[재학습] trainer.py 실행 시작...")
        result = subprocess.run(
            [sys.executable, "trainer.py"],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode == 0:
            print("[재학습] 완료. 모델 재로드 중...")
            model_store.reload()
            print("[재학습] 새 모델 로드 완료.")
        else:
            print(f"[재학습] 실패:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("[재학습] 타임아웃 (600초 초과)")
    except Exception as e:
        print(f"[재학습] 오류: {e}")
    finally:
        model_store.is_retraining = False


@app.post("/api/v1/retrain", tags=["모델"])
async def retrain(background_tasks: BackgroundTasks):
    """
    모델 재학습 트리거.
    백그라운드에서 trainer.py를 실행하고 즉시 응답 반환.
    재학습 중에는 기존 모델로 서비스 유지.
    """
    if model_store.is_retraining:
        return {"status": "already_retraining", "message": "이미 재학습이 진행 중입니다."}

    background_tasks.add_task(_retrain_background)
    return {
        "status":  "started",
        "message": "재학습이 백그라운드에서 시작되었습니다. /health로 완료 여부 확인하세요.",
        "note":    "재학습 중에도 기존 모델로 예측 서비스가 유지됩니다.",
    }


# ══════════════════════════════════════════════
# ⑨ 서버 실행
# ══════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",    # 모든 네트워크 인터페이스에서 접근 허용
        port=8000,
        reload=False,      # 운영 시 False (개발 중엔 True로 변경 가능)
        log_level="info",
    )
