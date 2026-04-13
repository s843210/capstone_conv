from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .feature_builder import build_feature_rows
from .inference_service import PredictionRow, run_inference
from .model_loader import ModelBundle
from .models import (
    DailyContext,
    DailySales,
    FeatureSnapshot,
    InventorySnapshot,
    JobRun,
    PredictionResult,
    TrainingDataset,
)
from .run_store import cleanup_old_runs, create_run_dir, save_json, save_text
from .schemas import DailyRunRequest, DailyRunResponse, JobStatusResponse
from .spring_client import SpringClient


class DailyRunService:
    def __init__(self, spring_client: SpringClient) -> None:
        self.spring_client = spring_client

    def run(self, db: Session, req: DailyRunRequest, bundle: ModelBundle) -> DailyRunResponse:
        run_id = f"{req.target_date.isoformat()}-{uuid4().hex[:8]}"
        run_dir = create_run_dir(run_id)
        validation_report = self._build_validation_report(req)

        run = JobRun(
            run_id=run_id,
            run_date=req.run_date,
            target_date=req.target_date,
            status="running",
            input_rows=len(req.items),
            predicted_rows=0,
            skipped_rows=0,
            spring_sent=0,
            spring_saved_count=0,
            error=None,
        )
        db.add(run)
        db.commit()

        save_json(
            run_dir,
            "request_summary.json",
            {
                "request": req.model_dump(by_alias=True, mode="json"),
                "validation": validation_report,
            },
        )

        try:
            if not validation_report["isValid"]:
                raise ValueError(validation_report["message"])

            self._upsert_context(db, req)
            self._upsert_inventory(db, req)
            self._upsert_sales(db, req)
            self._backfill_training_labels(db, req)

            sales_map = self._load_sales_map(db, req)
            feature_rows = build_feature_rows(bundle, req.target_date, req.items, req.context, sales_map)

            self._upsert_feature_snapshot(db, req, bundle, feature_rows)
            self._upsert_training_dataset(db, req, feature_rows)

            predicted_rows = run_inference(bundle, feature_rows)
            spring_payload = self._build_spring_payload(req, predicted_rows)
            save_json(run_dir, "payload.json", spring_payload)

            self._upsert_prediction_result(db, req, predicted_rows, bundle.version)
            db.commit()

            spring_sent = 0
            spring_saved_count = 0
            spring_error = None
            if req.dry_run:
                save_json(run_dir, "response.json", {"dryRun": True, "message": "spring push skipped"})
            else:
                push = self.spring_client.send_predictions(spring_payload)
                spring_sent = 1 if push.sent else 0
                spring_saved_count = push.saved_count
                spring_error = push.error
                save_json(
                    run_dir,
                    "response.json",
                    {
                        "statusCode": push.status_code,
                        "savedCount": push.saved_count,
                        "response": push.response_json,
                        "error": push.error,
                    },
                )

            if spring_error:
                run.status = "failed"
                run.error = spring_error
            else:
                run.status = "completed"
                run.error = None

            run.predicted_rows = len(predicted_rows)
            run.skipped_rows = max(0, len(req.items) - len(predicted_rows))
            run.spring_sent = spring_sent
            run.spring_saved_count = spring_saved_count
            db.commit()

            cleanup_old_runs()

            return DailyRunResponse(
                runId=run_id,
                targetDate=req.target_date,
                inputRows=len(req.items),
                predictedRows=len(predicted_rows),
                skippedRows=max(0, len(req.items) - len(predicted_rows)),
                springSent=spring_sent,
                springSavedCount=spring_saved_count,
                status=run.status,
                error=run.error,
            )

        except Exception as exc:
            db.rollback()
            run = db.get(JobRun, run_id)
            if run:
                run.status = "failed"
                run.error = str(exc)
                db.commit()
            save_text(run_dir, "errors.log", str(exc))
            raise

    @staticmethod
    def _build_validation_report(req: DailyRunRequest) -> dict:
        feature_date = req.target_date - timedelta(days=1)
        feature_date_match = feature_date == req.run_date

        required_start = feature_date - timedelta(days=13)
        sales_days_by_plu: dict[str, set] = defaultdict(set)
        for row in req.sales_history:
            if required_start <= row.sales_date <= feature_date:
                sales_days_by_plu[row.plu_code].add(row.sales_date)

        item_plu_codes = {item.plu_code for item in req.items}
        short_plu_codes = sorted(
            plu for plu in item_plu_codes if len(sales_days_by_plu.get(plu, set())) < 14
        )
        has_min_14_days = len(short_plu_codes) == 0

        message_parts = []
        if not feature_date_match:
            message_parts.append(
                f"feature_date({feature_date.isoformat()}) must equal runDate({req.run_date.isoformat()})"
            )
        if not has_min_14_days:
            sample = ", ".join(short_plu_codes[:10])
            message_parts.append(f"salesHistory must include at least 14 days for each item. short plu: {sample}")

        return {
            "featureDate": feature_date.isoformat(),
            "requiredSalesStartDate": required_start.isoformat(),
            "featureDateMatchRunDate": feature_date_match,
            "hasMin14DaysPerItem": has_min_14_days,
            "shortPluCodesCount": len(short_plu_codes),
            "isValid": feature_date_match and has_min_14_days,
            "message": "; ".join(message_parts) if message_parts else "ok",
        }

    def get_job(self, db: Session, run_id: str) -> JobStatusResponse | None:
        run = db.get(JobRun, run_id)
        if run is None:
            return None
        return JobStatusResponse(
            runId=run.run_id,
            runDate=run.run_date,
            targetDate=run.target_date,
            status=run.status,
            inputRows=run.input_rows,
            predictedRows=run.predicted_rows,
            skippedRows=run.skipped_rows,
            springSent=run.spring_sent,
            springSavedCount=run.spring_saved_count,
            error=run.error,
        )

    @staticmethod
    def _upsert_context(db: Session, req: DailyRunRequest) -> None:
        row = db.get(DailyContext, req.target_date)
        if row is None:
            row = DailyContext(target_date=req.target_date)
            db.add(row)

        row.avg_temp_c = req.context.avg_temp_c
        row.precipitation_mm = req.context.precipitation_mm
        row.is_rain = int(req.context.is_rain)
        row.is_holiday = int(req.context.is_holiday)
        row.academic_event = int(req.context.academic_event)
        row.building_headcount = int(req.context.building_headcount)

    @staticmethod
    def _upsert_inventory(db: Session, req: DailyRunRequest) -> None:
        existing_rows = db.execute(
            select(InventorySnapshot).where(InventorySnapshot.target_date == req.target_date)
        ).scalars().all()
        existing_map = {r.plu_code: r for r in existing_rows}

        for item in req.items:
            row = existing_map.get(item.plu_code)
            if row is None:
                row = InventorySnapshot(target_date=req.target_date, plu_code=item.plu_code)
                db.add(row)

            row.product_name = item.product_name
            row.category_l = item.category_l
            row.category_m = item.category_m
            row.category_s = item.category_s
            row.current_stock = int(item.current_stock)
            row.safety_stock_override = item.safety_stock

    @staticmethod
    def _upsert_sales(db: Session, req: DailyRunRequest) -> None:
        sales_dates = sorted({s.sales_date for s in req.sales_history})
        plu_codes = sorted({s.plu_code for s in req.sales_history})

        existing_rows = db.execute(
            select(DailySales).where(DailySales.sales_date.in_(sales_dates), DailySales.plu_code.in_(plu_codes))
        ).scalars().all()
        existing_map = {(r.sales_date, r.plu_code): r for r in existing_rows}

        for row_req in req.sales_history:
            key = (row_req.sales_date, row_req.plu_code)
            row = existing_map.get(key)
            if row is None:
                row = DailySales(sales_date=row_req.sales_date, plu_code=row_req.plu_code)
                db.add(row)
            row.sales_qty = int(row_req.sales_qty)

    @staticmethod
    def _backfill_training_labels(db: Session, req: DailyRunRequest) -> None:
        sales_dates = sorted({s.sales_date for s in req.sales_history})
        plu_codes = sorted({s.plu_code for s in req.sales_history})
        if not sales_dates or not plu_codes:
            return

        dataset_rows = db.execute(
            select(TrainingDataset).where(
                TrainingDataset.target_date.in_(sales_dates),
                TrainingDataset.plu_code.in_(plu_codes),
            )
        ).scalars().all()
        dataset_map = {(r.target_date, r.plu_code): r for r in dataset_rows}

        now = datetime.utcnow()
        for row_req in req.sales_history:
            key = (row_req.sales_date, row_req.plu_code)
            target = dataset_map.get(key)
            if target is not None:
                target.target_sales = int(row_req.sales_qty)
                target.labeled_at = now

    @staticmethod
    def _load_sales_map(db: Session, req: DailyRunRequest) -> dict[str, dict]:
        feature_date = req.target_date - timedelta(days=1)
        start_date = feature_date - timedelta(days=60)
        plu_codes = sorted({i.plu_code for i in req.items})

        rows = db.execute(
            select(DailySales).where(
                DailySales.plu_code.in_(plu_codes),
                DailySales.sales_date >= start_date,
                DailySales.sales_date <= feature_date,
            )
        ).scalars().all()

        sales_map: dict[str, dict] = defaultdict(dict)
        for row in rows:
            sales_map[row.plu_code][row.sales_date] = int(row.sales_qty)
        return sales_map

    @staticmethod
    def _upsert_feature_snapshot(db: Session, req: DailyRunRequest, bundle: ModelBundle, feature_rows) -> None:
        plu_codes = [r.plu_code for r in feature_rows]
        if not plu_codes:
            return

        existing_rows = db.execute(
            select(FeatureSnapshot).where(
                FeatureSnapshot.target_date == req.target_date,
                FeatureSnapshot.plu_code.in_(plu_codes),
            )
        ).scalars().all()
        existing_map = {r.plu_code: r for r in existing_rows}

        for row_data in feature_rows:
            row = existing_map.get(row_data.plu_code)
            if row is None:
                row = FeatureSnapshot(target_date=req.target_date, plu_code=row_data.plu_code)
                db.add(row)
            row.feature_profile = bundle.profile
            row.raw_features = row_data.raw_features
            row.model_features = row_data.model_features

    @staticmethod
    def _upsert_training_dataset(db: Session, req: DailyRunRequest, feature_rows) -> None:
        plu_codes = [r.plu_code for r in feature_rows]
        if not plu_codes:
            return

        existing_rows = db.execute(
            select(TrainingDataset).where(
                TrainingDataset.target_date == req.target_date,
                TrainingDataset.plu_code.in_(plu_codes),
            )
        ).scalars().all()
        existing_map = {r.plu_code: r for r in existing_rows}

        for row_data in feature_rows:
            row = existing_map.get(row_data.plu_code)
            if row is None:
                row = TrainingDataset(
                    target_date=req.target_date,
                    plu_code=row_data.plu_code,
                    features=row_data.raw_features,
                    target_sales=None,
                )
                db.add(row)
            else:
                row.features = row_data.raw_features

    @staticmethod
    def _build_spring_payload(req: DailyRunRequest, predictions: list[PredictionRow]) -> dict:
        by_category: dict[str, list[PredictionRow]] = defaultdict(list)
        for p in predictions:
            by_category[p.category_m_name].append(p)

        categories_payload = []
        for category_name in sorted(by_category.keys()):
            rows = by_category[category_name]
            total_order = int(sum(r.recommended_order for r in rows))
            avg_conf = float(sum(r.confidence_score for r in rows) / len(rows)) if rows else 0.0
            ai_message = f"{category_name} {len(rows)}개 상품, 총발주 {total_order}, 평균신뢰도 {avg_conf:.0%}"

            products_payload = [
                {
                    "pluCode": r.plu_code,
                    "predictedSales": int(r.predicted_sales),
                    "recommendedOrder": int(r.recommended_order),
                    "confidenceScore": float(r.confidence_score),
                }
                for r in rows
            ]

            categories_payload.append(
                {
                    "categoryName": category_name,
                    "totalRecommendedOrder": total_order,
                    "aiMessage": ai_message,
                    "products": products_payload,
                }
            )

        return {
            "targetDate": req.target_date.isoformat(),
            "categories": categories_payload,
        }

    @staticmethod
    def _upsert_prediction_result(db: Session, req: DailyRunRequest, predictions: list[PredictionRow], model_version: str) -> None:
        plu_codes = [p.plu_code for p in predictions]
        if not plu_codes:
            return

        grouped: dict[str, list[PredictionRow]] = defaultdict(list)
        for p in predictions:
            grouped[p.category_m_name].append(p)

        category_message: dict[str, str] = {}
        for category_name, rows in grouped.items():
            total_order = int(sum(r.recommended_order for r in rows))
            avg_conf = float(sum(r.confidence_score for r in rows) / len(rows)) if rows else 0.0
            category_message[category_name] = (
                f"{category_name} {len(rows)}개 상품, 총발주 {total_order}, 평균신뢰도 {avg_conf:.0%}"
            )

        existing_rows = db.execute(
            select(PredictionResult).where(
                PredictionResult.target_date == req.target_date,
                PredictionResult.plu_code.in_(plu_codes),
            )
        ).scalars().all()
        existing_map = {r.plu_code: r for r in existing_rows}

        for p in predictions:
            row = existing_map.get(p.plu_code)
            if row is None:
                row = PredictionResult(target_date=req.target_date, plu_code=p.plu_code, product_name=p.product_name)
                db.add(row)
            row.product_name = p.product_name
            row.category_m = p.category_m_name
            row.predicted_sales = int(p.predicted_sales)
            row.recommended_order = int(p.recommended_order)
            row.confidence_score = float(p.confidence_score)
            row.ai_message = category_message.get(p.category_m_name, "")
            row.model_version = model_version
