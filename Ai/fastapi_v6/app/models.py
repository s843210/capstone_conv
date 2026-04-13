from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class DailySales(Base):
    __tablename__ = "daily_sales"
    __table_args__ = (UniqueConstraint("sales_date", "plu_code", name="uq_daily_sales_date_plu"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sales_date: Mapped[date] = mapped_column(Date, nullable=False)
    plu_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sales_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class DailyContext(Base):
    __tablename__ = "daily_context"

    target_date: Mapped[date] = mapped_column(Date, primary_key=True)
    avg_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_rain: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_holiday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    academic_event: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    building_headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshot"
    __table_args__ = (UniqueConstraint("target_date", "plu_code", name="uq_inventory_target_plu"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plu_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_l: Mapped[str] = mapped_column(String(100), nullable=False, default="_unknown")
    category_m: Mapped[str] = mapped_column(String(100), nullable=False, default="_unknown")
    category_s: Mapped[str] = mapped_column(String(100), nullable=False, default="_unknown")
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safety_stock_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshot"
    __table_args__ = (UniqueConstraint("target_date", "plu_code", name="uq_feature_target_plu"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plu_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feature_profile: Mapped[str] = mapped_column(String(32), nullable=False, default="small")
    raw_features: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_features: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class PredictionResult(Base):
    __tablename__ = "prediction_result"
    __table_args__ = (UniqueConstraint("target_date", "plu_code", name="uq_prediction_target_plu"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plu_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_m: Mapped[str] = mapped_column(String(100), nullable=False, default="_unknown")
    predicted_sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommended_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ai_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v6")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class TrainingDataset(Base):
    __tablename__ = "training_dataset"
    __table_args__ = (UniqueConstraint("target_date", "plu_code", name="uq_training_target_plu"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plu_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    target_sales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    labeled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class JobRun(Base):
    __tablename__ = "job_run"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    input_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    predicted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spring_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spring_saved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
