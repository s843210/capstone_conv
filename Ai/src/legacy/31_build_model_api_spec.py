from __future__ import annotations

import json
from pathlib import Path

import joblib


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "outputs" / "models" / "random_forest_fast_model.pkl"
OUT_MD = BASE_DIR / "outputs" / "reports" / "model_api_spec.md"


FEATURE_DESCRIPTIONS = {
    "plu_code": "상품 PLU 코드 (원본 문자열, 서버에서 LabelEncoding 매핑 적용)",
    "product_category": "상품 카테고리 (원본 문자열, 서버에서 LabelEncoding 매핑 적용)",
    "sales_qty": "기준일 실제 판매수량",
    "purchase_qty": "기준일 매입수량",
    "is_start_semester": "개강일 여부 (0/1)",
    "is_end_semester": "종강일 여부 (0/1)",
    "is_exam": "시험기간 여부 (0/1)",
    "is_vacation": "방학 여부 (0/1)",
    "is_festival": "축제 여부 (0/1)",
    "is_holiday_or_no_class": "휴강/공휴일/휴업 여부 (0/1)",
    "class_count": "해당 요일 전체 수업량 지표",
    "monday_class_count": "월요일 수업 수",
    "tuesday_class_count": "화요일 수업 수",
    "wednesday_class_count": "수요일 수업 수",
    "thursday_class_count": "목요일 수업 수",
    "friday_class_count": "금요일 수업 수",
    "year": "기준일 연도",
    "month": "기준일 월",
    "day": "기준일 일",
    "weekday": "요일 인덱스 (월=0, ..., 일=6)",
    "is_weekend": "주말 여부 (0/1)",
    "sales_lag_1": "동일 상품 1일 전 판매량",
    "sales_lag_7": "동일 상품 7일 전 판매량",
    "rolling_mean_7": "동일 상품 최근 7일 이동평균 (현재일 제외)",
    "rolling_mean_14": "동일 상품 최근 14일 이동평균 (현재일 제외)",
    "rolling_mean_28": "동일 상품 최근 28일 이동평균 (현재일 제외)",
}


def main() -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    bundle = joblib.load(MODEL_PATH)
    feature_cols = bundle.get("feature_cols", [])
    categorical_cols = bundle.get("categorical_cols", [])
    label_maps = bundle.get("label_maps", {})

    if not feature_cols:
        raise ValueError("feature_cols not found in model bundle.")

    example_payload = {}
    for c in feature_cols:
        if c == "plu_code":
            example_payload[c] = "8801056040925.0"
        elif c == "product_category":
            example_payload[c] = "음료"
        elif c in {"year"}:
            example_payload[c] = 2026
        elif c in {"month"}:
            example_payload[c] = 2
        elif c in {"day"}:
            example_payload[c] = 2
        elif c in {"weekday"}:
            example_payload[c] = 0
        elif c in {"is_weekend", "is_start_semester", "is_end_semester", "is_exam", "is_vacation", "is_festival", "is_holiday_or_no_class"}:
            example_payload[c] = 0
        else:
            example_payload[c] = 5.0

    sample_request = {
        "base_date": "2026-02-01",
        "items": [
            {
                "plu_code": "8801056040925.0",
                "product_name": "롯데)칠성사이다캔355ml",
                "product_category": "음료",
                "features": example_payload,
            }
        ],
        "safety_factor": 1.2,
    }

    sample_response = {
        "base_date": "2026-02-01",
        "predict_date": "2026-02-02",
        "results": [
            {
                "plu_code": "8801056040925.0",
                "product_name": "롯데)칠성사이다캔355ml",
                "product_category": "음료",
                "predicted_sales_qty": 18.42,
                "recommended_order_qty": 23,
            }
        ],
    }

    lines: list[str] = []
    lines.append("# Model API Spec (RandomForest Fast)")
    lines.append("")
    lines.append("## 1. Model File")
    lines.append(f"- Path: `{MODEL_PATH.as_posix()}`")
    lines.append("- Type: `RandomForestRegressor` bundle (`model`, `feature_cols`, `categorical_cols`, `label_maps`)")
    lines.append("")
    lines.append("## 2. Feature Schema")
    lines.append("| feature | type | description |")
    lines.append("|---|---|---|")
    for c in feature_cols:
        t = "string" if c in categorical_cols else "number"
        desc = FEATURE_DESCRIPTIONS.get(c, "모델 입력 feature")
        lines.append(f"| `{c}` | `{t}` | {desc} |")
    lines.append("")
    lines.append("## 3. Preprocessing Rules")
    lines.append("- 입력 feature는 학습 시 사용 순서와 동일한 `feature_cols` 순서로 구성해야 합니다.")
    lines.append("- 범주형 컬럼(`plu_code`, `product_category`)은 **LabelEncoding**을 사용합니다.")
    lines.append("- 학습 시점에 없는 신규 범주값은 `-1`로 매핑합니다.")
    lines.append("- 수치형 컬럼 결측/비정상값은 `0`으로 대체합니다.")
    lines.append("- 예측값이 음수면 최종 응답에서 `0`으로 보정합니다.")
    lines.append("")
    lines.append("## 4. Categorical Encoding Info")
    for c in categorical_cols:
        n_cls = len(label_maps.get(c, {}))
        lines.append(f"- `{c}` classes: `{n_cls}`")
    lines.append("")
    lines.append("## 5. Sample Request JSON")
    lines.append("```json")
    lines.append(json.dumps(sample_request, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## 6. Sample Response JSON")
    lines.append("```json")
    lines.append(json.dumps(sample_response, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## 7. Prediction Flow")
    lines.append("1. 입력 수신: `base_date`, 상품 메타정보, feature 값")
    lines.append("2. feature 생성/정렬: 학습과 동일한 `feature_cols` 기준으로 입력 벡터 구성")
    lines.append("3. 범주형 인코딩: `label_maps`로 LabelEncoding 적용(미등록 값은 `-1`)")
    lines.append("4. 모델 예측: `model.predict(X)`로 `predicted_sales_qty` 계산")
    lines.append("5. 발주 추천 계산: `recommended_order_qty = ceil(predicted_sales_qty * safety_factor)`")
    lines.append("6. 음수 보정: `predicted_sales_qty <= 0`이면 추천 발주량 `0`")
    lines.append("")
    lines.append("## 8. Order Recommendation Formula")
    lines.append("- `recommended_order_qty = ceil(predicted_sales_qty * safety_factor)`")
    lines.append("- 기본 `safety_factor = 1.2`")
    lines.append("- `predicted_sales_qty <= 0` 인 경우 `recommended_order_qty = 0`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved API spec: {OUT_MD}")
    print(f"Feature count: {len(feature_cols)}")
    print(f"Categorical columns: {categorical_cols}")


if __name__ == "__main__":
    main()
