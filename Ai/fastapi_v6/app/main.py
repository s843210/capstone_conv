from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .model_loader import model_store
from .schemas import DailyRunRequest, DailyRunResponse, ErrorResponse, JobStatusResponse
from .service import DailyRunService
from .spring_client import SpringClient


spring_client = SpringClient()
run_service = DailyRunService(spring_client=spring_client)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    try:
        model_store.load()
    except Exception as exc:
        # Allow startup for Swagger/docs verification even when model artifacts are missing.
        print(f"[WARN] model load skipped: {exc}")
    yield


app = FastAPI(
    title="CONV FastAPI v6 Inference API",
    version="1.1.0",
    description=(
        "Spring server가 준비되기 전 단계에서 사용할 수 있는 AI 추론 API입니다.\n\n"
        "- 배치 입력 수신\n"
        "- feature 생성/추론\n"
        "- Spring `/api/ai/predictions` 규격 payload 생성 및 전송\n"
        "- 실행 이력/아티팩트 저장\n\n"
        "Swagger UI: `/docs`, OpenAPI JSON: `/openapi.json`"
    ),
    contact={"name": "CONV AI Team"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", tags=["System"], summary="Health Check")
def health(db: Session = Depends(get_db)) -> dict:
    bundle = model_store.bundle
    if bundle is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "modelVersion": bundle.version,
        "profile": bundle.profile,
        "featureCount": len(bundle.feature_cols),
    }


@app.post(
    "/api/v1/jobs/daily-run",
    response_model=DailyRunResponse,
    tags=["Jobs"],
    summary="Run Daily Prediction Job",
    description=(
        "일 배치 입력을 받아 추론을 수행하고 Spring 서버로 결과를 전송합니다. "
        "`targetDate == runDate + 1` 규칙과 최근 14일 이력 검증을 수행합니다."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
def run_daily_job(req: DailyRunRequest, db: Session = Depends(get_db)) -> DailyRunResponse:
    bundle = model_store.bundle
    if bundle is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    try:
        return run_service.run(db, req, bundle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/jobs/{run_id}",
    response_model=JobStatusResponse,
    tags=["Jobs"],
    summary="Get Job Status",
    responses={404: {"model": ErrorResponse, "description": "Run id not found"}},
)
def get_job_status(run_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    row = run_service.get_job(db, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return row
