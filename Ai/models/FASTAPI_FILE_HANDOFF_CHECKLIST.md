# FastAPI 전달 체크리스트

팀원에게 파일 전달할 때 아래 내용은 반드시 포함해주세요.

## 1) 필수 전달 파일
- `random_forest_fast_model.pkl`
- `model_api_spec.md`
- `requirements.txt`

## 2) 권장 추가 파일 (있으면 좋음)
- `32_interactive_prediction_test.py` (로컬 콘솔 테스트용)
- `tomorrow_sales_prediction.csv` (예측 결과 예시)
- `FASTAPI_HANDOFF_NOTE.txt` (간단 인수인계 메모)

## 3) 전달 시 꼭 같이 안내할 내용
- 모델 파일은 학습 완료 모델이며 재학습 없이 바로 추론 가능
- 입력 feature는 `model_api_spec.md`의 **feature schema와 순서**를 따라야 함
- 범주형 컬럼(`plu_code`, `product_category`)은 **LabelEncoding** 적용
- 학습 시점에 없던 범주값은 `-1`로 처리
- 예측값이 음수면 `0`으로 보정
- 추천 발주 공식:
  - `recommended_order_qty = ceil(predicted_sales_qty * safety_factor)`
  - 기본 `safety_factor = 1.2`

## 4) 빠른 수신 확인 체크
- `pip install -r requirements.txt` 성공
- `random_forest_fast_model.pkl` 로드 성공
- 샘플 입력 1건에 대해 `predict()` 응답 확인
- 응답에 `predicted_sales_qty`, `recommended_order_qty` 포함 확인

## 5) 최소 전달 세트 요약
아래 3개만 있어도 FastAPI 연동은 가능합니다.
1. `random_forest_fast_model.pkl`
2. `model_api_spec.md`
3. `requirements.txt`
