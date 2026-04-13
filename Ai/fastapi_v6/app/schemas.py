from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SalesHistoryItem(BaseSchema):
    sales_date: date = Field(alias="salesDate")
    plu_code: str = Field(alias="pluCode", min_length=1)
    sales_qty: int = Field(alias="salesQty", ge=0)


class InventoryItem(BaseSchema):
    plu_code: str = Field(alias="pluCode", min_length=1)
    product_name: str = Field(alias="productName", min_length=1)
    category_l: str = Field(alias="categoryL", default="_unknown")
    category_m: str = Field(alias="categoryM", default="_unknown")
    category_s: str = Field(alias="categoryS", default="_unknown")
    current_stock: int = Field(alias="currentStock", ge=0)
    safety_stock: int | None = Field(default=None, alias="safetyStock", ge=0)


class ContextPayload(BaseSchema):
    avg_temp_c: float | None = Field(default=None, alias="avgTempC")
    precipitation_mm: float | None = Field(default=None, alias="precipitationMm")
    is_rain: int = Field(default=0, alias="isRain")
    is_holiday: int = Field(default=0, alias="isHoliday")
    academic_event: int = Field(default=0, alias="academicEvent")
    building_headcount: int = Field(default=0, alias="buildingHeadcount")


class DailyRunRequest(BaseSchema):
    run_date: date = Field(alias="runDate")
    target_date: date = Field(alias="targetDate")
    sales_history: list[SalesHistoryItem] = Field(alias="salesHistory", min_length=1)
    items: list[InventoryItem] = Field(min_length=1)
    context: ContextPayload
    dry_run: bool = Field(default=False, alias="dryRun")


class DailyRunResponse(BaseSchema):
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
