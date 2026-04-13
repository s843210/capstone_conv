# FastAPI-Spring v6 재현 파이프라인 구현 요약

## 구현 범위
- FastAPI 전용 구현 (Spring 코드 미수정)
- v6 모델 아티팩트 로드 + parity 추론
- 일배치 입력 수신/적재/피처생성/추론/Spring 전송

## API
- `GET /health`
- `POST /api/v1/jobs/daily-run`
- `GET /jobs/{run_id}`

## 저장 테이블
- `daily_sales`
- `daily_context`
- `inventory_snapshot`
- `feature_snapshot`
- `prediction_result`
- `training_dataset`
- `job_run`

## 핵심 규칙
- `feature_date = target_date - 1`
- `lag_1/3/7`, `rolling_7_*` FastAPI 자동 계산
- `meta.feature_cols` 순서 강제 + `log_transform_cols` 동일 적용
- 예측값 `expm1` 역변환 후 정수화
- `recommended_order = max(0, ceil(predicted + safety - current_stock))`

## 파일 위치
- 서버 엔트리: `Ai/fastapi_v6/main.py`
- 앱: `Ai/fastapi_v6/app/`
- 환경: `Ai/fastapi_v6/.env.example`
- 의존성: `Ai/fastapi_v6/requirements.txt`
