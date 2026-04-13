from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import log1p

from .model_loader import ModelBundle
from .order_policy import calc_safety_stock
from .schemas import ContextPayload, InventoryItem


@dataclass
class FeatureRow:
    plu_code: str
    product_name: str
    category_m_name: str
    current_stock: int
    safety_stock: int
    raw_features: dict[str, float]
    model_features: dict[str, float]


def _sales_value(sales_map: dict[str, dict[date, int]], plu_code: str, day: date) -> int:
    return int(sales_map.get(plu_code, {}).get(day, 0))


def _rolling(sales_map: dict[str, dict[date, int]], plu_code: str, end_date: date, window: int) -> tuple[float, float]:
    values = [_sales_value(sales_map, plu_code, end_date - timedelta(days=i)) for i in range(1, window + 1)]
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return float(mean), float(variance ** 0.5)


def build_feature_rows(
    bundle: ModelBundle,
    target_date: date,
    items: list[InventoryItem],
    context: ContextPayload,
    sales_map: dict[str, dict[date, int]],
) -> list[FeatureRow]:
    feature_date = target_date - timedelta(days=1)
    day_of_week = feature_date.weekday()  # 월=0 .. 일=6
    month = feature_date.month
    is_weekend = 1 if day_of_week >= 5 else 0
    is_holiday = int(context.is_holiday) if context.is_holiday in (0, 1) else is_weekend
    academic_event = int(context.academic_event or 0)

    rows: list[FeatureRow] = []
    for item in items:
        lag_1 = _sales_value(sales_map, item.plu_code, feature_date - timedelta(days=1))
        lag_3 = _sales_value(sales_map, item.plu_code, feature_date - timedelta(days=3))
        lag_7 = _sales_value(sales_map, item.plu_code, feature_date - timedelta(days=7))
        rolling_7_mean, rolling_7_std = _rolling(sales_map, item.plu_code, feature_date, 7)

        lag_14 = _sales_value(sales_map, item.plu_code, feature_date - timedelta(days=14))
        rolling_14_mean, rolling_14_std = _rolling(sales_map, item.plu_code, feature_date, 14)

        category_l_encoded = bundle.encode_category_l(item.category_l)
        category_m_encoded = bundle.encode_category_m(item.category_m)

        safety_stock = item.safety_stock
        if safety_stock is None:
            safety_stock = calc_safety_stock(item.category_m, rolling_7_mean)

        raw_features: dict[str, float] = {
            "lag_1": float(lag_1),
            "lag_3": float(lag_3),
            "lag_7": float(lag_7),
            "rolling_7_mean": float(rolling_7_mean),
            "rolling_7_std": float(rolling_7_std),
            "day_of_week": float(day_of_week),
            "month": float(month),
            "is_holiday": float(is_holiday),
            "academic_event": float(academic_event),
            "building_headcount": float(context.building_headcount or 0),
            "avg_temp_c": float(context.avg_temp_c or 0),
            "precipitation_mm": float(context.precipitation_mm or 0),
            "is_rain": float(context.is_rain or 0),
            "category_l": float(category_l_encoded),
            "category_m": float(category_m_encoded),
            "day_of_month": float(feature_date.day),
            "is_weekend": float(is_weekend),
            "lag_14": float(lag_14),
            "rolling_14_mean": float(rolling_14_mean),
            "rolling_14_std": float(rolling_14_std),
            "safety_stock": float(safety_stock),
        }

        # v6 medium/large에서 쓰는 academic_event one-hot 대응
        for event_code in range(1, 6):
            raw_features[f"acad_{event_code}"] = 1.0 if academic_event == event_code else 0.0

        model_features = dict(raw_features)
        for col in bundle.log_transform_cols:
            if col in model_features:
                model_features[col] = float(log1p(max(0.0, model_features[col])))

        # meta.feature_cols 기준 컬럼 강제 정렬 + 없는 컬럼 기본값 0
        model_features = {col: float(model_features.get(col, 0.0)) for col in bundle.feature_cols}

        rows.append(
            FeatureRow(
                plu_code=item.plu_code,
                product_name=item.product_name,
                category_m_name=item.category_m,
                current_stock=int(item.current_stock),
                safety_stock=int(safety_stock),
                raw_features=raw_features,
                model_features=model_features,
            )
        )

    return rows
