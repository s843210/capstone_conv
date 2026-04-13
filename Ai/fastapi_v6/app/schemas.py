from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SalesHistoryItem(BaseSchema):
    sales_date: date = Field(alias="salesDate", description="Sales date (YYYY-MM-DD)")
    plu_code: str = Field(alias="pluCode", min_length=1, description="PLU code")
    sales_qty: int = Field(alias="salesQty", ge=0, description="Daily sales quantity")


class InventoryItem(BaseSchema):
    plu_code: str = Field(alias="pluCode", min_length=1, description="PLU code")
    product_name: str = Field(alias="productName", min_length=1, description="Product name")
    category_l: str = Field(alias="categoryL", default="_unknown")
    category_m: str = Field(alias="categoryM", default="_unknown")
    category_s: str = Field(alias="categoryS", default="_unknown")
    current_stock: int = Field(alias="currentStock", ge=0, description="Current inventory stock")
    safety_stock: int | None = Field(default=None, alias="safetyStock", ge=0)


class ContextPayload(BaseSchema):
    avg_temp_c: float | None = Field(default=None, alias="avgTempC")
    precipitation_mm: float | None = Field(default=None, alias="precipitationMm")
    is_rain: int = Field(default=0, alias="isRain")
    is_holiday: int = Field(default=0, alias="isHoliday")
    academic_event: int = Field(default=0, alias="academicEvent")
    building_headcount: int = Field(default=0, alias="buildingHeadcount")


class DailyRunRequest(BaseSchema):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "runDate": "2026-04-13",
                "targetDate": "2026-04-14",
                "salesHistory": [
                    {"salesDate": "2026-04-12", "pluCode": "15000001", "salesQty": 7},
                    {"salesDate": "2026-04-11", "pluCode": "15000001", "salesQty": 5},
                ],
                "items": [
                    {
                        "pluCode": "15000001",
                        "productName": "참치마요 삼각김밥",
                        "categoryL": "간편식품",
                        "categoryM": "삼각김밥",
                        "categoryS": "참치마요",
                        "currentStock": 2,
                    }
                ],
                "context": {
                    "avgTempC": 17.2,
                    "precipitationMm": 0.0,
                    "isRain": 0,
                    "isHoliday": 0,
                    "academicEvent": 0,
                    "buildingHeadcount": 730,
                },
                "dryRun": False,
            }
        },
    )

    run_date: date = Field(alias="runDate", description="Run date (normally today)")
    target_date: date = Field(alias="targetDate", description="Prediction target date (normally runDate + 1)")
    sales_history: list[SalesHistoryItem] = Field(
        alias="salesHistory",
        min_length=1,
        description="Historical sales rows. At least 14 recent days per item are recommended.",
    )
    items: list[InventoryItem] = Field(min_length=1, description="Target inventory items")
    context: ContextPayload
    dry_run: bool = Field(default=False, alias="dryRun", description="Skip Spring push when true")

    @model_validator(mode="after")
    def validate_target_date_rule(self) -> "DailyRunRequest":
        expected_target = self.run_date.toordinal() + 1
        if self.target_date.toordinal() != expected_target:
            raise ValueError("targetDate must be runDate + 1 day")
        return self


class DailyRunResponse(BaseSchema):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "runId": "2026-04-14-a1b2c3d4",
                "targetDate": "2026-04-14",
                "inputRows": 25,
                "predictedRows": 25,
                "skippedRows": 0,
                "springSent": 1,
                "springSavedCount": 25,
                "status": "completed",
                "error": None,
            }
        },
    )

    run_id: str = Field(alias="runId")
    target_date: date = Field(alias="targetDate")
    input_rows: int = Field(alias="inputRows")
    predicted_rows: int = Field(alias="predictedRows")
    skipped_rows: int = Field(alias="skippedRows")
    spring_sent: int = Field(alias="springSent")
    spring_saved_count: int = Field(alias="springSavedCount")
    status: str
    error: str | None = None


class JobStatusResponse(BaseSchema):
    run_id: str = Field(alias="runId")
    run_date: date = Field(alias="runDate")
    target_date: date = Field(alias="targetDate")
    status: str
    input_rows: int = Field(alias="inputRows")
    predicted_rows: int = Field(alias="predictedRows")
    skipped_rows: int = Field(alias="skippedRows")
    spring_sent: int = Field(alias="springSent")
    spring_saved_count: int = Field(alias="springSavedCount")
    error: str | None = None


class ErrorResponse(BaseSchema):
    detail: str | dict[str, Any] | list[Any]
