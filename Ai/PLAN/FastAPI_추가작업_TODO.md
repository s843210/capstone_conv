# FastAPI 팀 추가 작업 TODO

기준 구현: `/Users/limbohyun21/Documents/GitHub/capstone_conv/Ai/fastapi_v6`
기준 날짜: 2026-04-13

## 1) 서버 기동 준비
- `Ai/fastapi_v6/.venv` 활성화 후 `pip install -r requirements.txt`
- `Ai/fastapi_v6/.env` 생성 (`.env.example` 복사)
- 모델 아티팩트 3종 배치
- `MODEL_PATH` -> `rf_sales_forecast_v6.pkl`
- `ENCODER_PATH` -> `label_encoders_v6.pkl`
- `META_PATH` -> `model_meta_v6.json`
- `python main.py` 실행 후 `/health` 200 확인

## 2) 데이터 초기 적재(백필)
- 과거 feature CSV를 `scripts/import_features_csv.py`로 1회 적재
- 적재 후 SQLite 테이블 건수 확인
- `daily_sales`
- `daily_context`
- `training_dataset`

## 3) 일배치 API 안정화
- `POST /api/v1/jobs/daily-run` 요청 스키마 고정 유지
- 스프링 요청에서 `salesHistory` 최소 14일 보장 여부 검증 로그 추가
- `targetDate` 기준 `feature_date = targetDate - 1` 규칙 검증 로그 추가
- `run_id` 단위 아티팩트(`request_summary.json`, `payload.json`, `response.json`, `errors.log`) 유지

## 4) 추론 품질/정합성 점검
- `meta.feature_cols` 순서 강제 적용 확인
- `log_transform_cols`가 meta 기준으로 적용되는지 샘플 검증
- `predicted_sales = expm1 -> round -> max(0)` 규칙 확인
- `recommended_order = max(0, ceil(predicted + safety - stock))` 규칙 확인
- `confidence_score` 값 범위(0~1) 검증

## 5) 라벨 백필 확인
- 다음날 `salesHistory(sales_date=T)` 입력 시 `training_dataset(target_date=T)`의 `target_sales` 채워지는지 확인
- 백필 완료 행과 미완료 행을 구분 조회하는 SQL 템플릿 준비

## 6) 운영 전 체크
- SQLite 잠금 이슈 대응: 조회 시 `PRAGMA busy_timeout=5000` 기준 공유
- 운영 전 PostgreSQL 전환 여부 결정 (현재는 SQLite 운영)
- 실패 기준 정의: Spring push 실패 시 `job_run.status=failed` + `error` 기록 확인

## 7) 수용 기준(DoD)
- `/health` 정상
- 샘플 `daily-run` 1회 성공
- `prediction_result` 건수 > 0
- Spring `savedCount` 파싱 정상
- `job_run`에 실행 결과 기록 정상
