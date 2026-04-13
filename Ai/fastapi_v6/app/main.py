from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .model_loader import model_store
from .schemas import DailyRunRequest, DailyRunResponse, JobStatusResponse
from .service import DailyRunService
from .spring_client import SpringClient


spring_client = SpringClient()
run_service = DailyRunService(spring_client=spring_client)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    model_store.load()
    yield


app = FastAPI(
    title="CONV FastAPI v6 Inference Server",
    version="1.0.0",
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


@app.get("/health")
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


@app.post("/api/v1/jobs/daily-run", response_model=DailyRunResponse)
def run_daily_job(req: DailyRunRequest, db: Session = Depends(get_db)) -> DailyRunResponse:
    bundle = model_store.bundle
    if bundle is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    try:
        return run_service.run(db, req, bundle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/jobs/{run_id}", response_model=JobStatusResponse)
def get_job_status(run_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    row = run_service.get_job(db, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return row
