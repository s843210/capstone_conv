# CONV FastAPI v6

Spring 서버가 준비되기 전에도 AI 배치 추론을 독립적으로 실행할 수 있는 FastAPI 서버입니다.

## Endpoints

- `GET /health`
- `POST /api/v1/jobs/daily-run`
- `GET /jobs/{run_id}`

Swagger:

- `GET /docs` (Swagger UI)
- `GET /openapi.json` (친구에게 전달 가능한 OpenAPI JSON)

## Validation Rules

- `targetDate == runDate + 1`
- `feature_date = targetDate - 1` 이고 `feature_date == runDate`
- 요청 `items`의 각 `pluCode`마다 최근 14일(`feature_date-13` ~ `feature_date`) `salesHistory` 존재 필요

검증 결과는 실행 아티팩트의 `request_summary.json`에 함께 기록됩니다.

## Quick Start

```bash
cd Ai/fastapi_v6
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

## Swagger 전달 방법

서버 실행 후 아래 파일을 전달하면 됩니다.

```bash
curl http://127.0.0.1:8000/openapi.json -o openapi.json
```

## Spring 연동

- 대상 API: `POST {SPRING_BASE_URL}{SPRING_AI_PATH}`
- 기본값: `http://127.0.0.1:8080/api/ai/predictions`
- `dryRun=true`면 Spring 전송을 건너뜁니다.
