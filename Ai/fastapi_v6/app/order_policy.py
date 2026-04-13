from __future__ import annotations

from math import ceil


SAFETY_MULTIPLIERS = {
    "담배": 1.0,
    "음료": 0.5,
    "과자": 0.5,
    "캔디": 0.5,
    "초콜릿": 0.5,
    "초콜렛": 0.5,
    "젤리": 0.5,
    "유제품": 0.5,
    "커피": 0.5,
    "생수": 0.5,
    "도시락": 0.3,
    "김밥": 0.3,
    "삼각": 0.3,
    "밥류": 0.3,
    "빵": 0.3,
    "샌드위치": 0.3,
}


def calc_safety_stock(category_m: str, rolling_7_mean: float) -> int:
    multiplier = 0.3
    text = str(category_m or "")
    for key, value in SAFETY_MULTIPLIERS.items():
        if key in text:
            multiplier = value
            break
    return max(0, round(max(0.0, float(rolling_7_mean)) * multiplier))


def calc_recommended_order(predicted_sales: int, safety_stock: int, current_stock: int) -> int:
    return max(0, int(ceil(predicted_sales + safety_stock - current_stock)))
