# FastAPI v6 Inference Server

`rf_sales_forecast_v6.py` 학습 규칙을 서빙에서 재현하는 FastAPI 서버입니다.

## 포함 기능
- `POST /api/v1/jobs/daily-run`
  - Spring에서 일배치 입력(`salesHistory`, `items`, `context`)을 보내면
  - FastAPI가 `lag/rolling` 자동 생성 → v6 추론 → 권장발주 계산
  - Spring `POST /api/ai/predictions`로 결과 전송
  - 입력/피처/예측을 FastAPI DB에 누적 저장
- `GET /health`
- `GET /jobs/{run_id}`

## 실행
```bash
cd /Users/limbohyun21/Documents/GitHub/capstone_conv/Ai/fastapi_v6
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

기본 DB는 SQLite(`fastapi_v6.sqlite3`)로 설정되어 있습니다.

## 요청 예시
```json
{
  "runDate": "2026-04-13",
  "targetDate": "2026-04-14",
  "salesHistory": [
    {"salesDate": "2026-04-12", "pluCode": "15000001", "salesQty": 7},
    {"salesDate": "2026-04-11", "pluCode": "15000001", "salesQty": 5}
  ],
  "items": [
    {
      "pluCode": "15000001",
      "productName": "참치마요 삼각김밥",
      "categoryL": "간편식품",
      "categoryM": "삼각김밥",
      "categoryS": "참치마요",
      "currentStock": 2
    }
  ],
  "context": {
    "avgTempC": 17.2,
    "precipitationMm": 0.0,
    "isRain": 0,
    "isHoliday": 0,
    "academicEvent": 0,
    "buildingHeadcount": 730
  },
  "dryRun": false
}
```

## 모델 파일
기본 경로(환경변수로 변경 가능):
- `MODEL_PATH`: `Ai/fastapi_v6/saved_models/rf_sales_forecast_v6.pkl`
- `ENCODER_PATH`: `Ai/fastapi_v6/saved_models/label_encoders_v6.pkl`
- `META_PATH`: `Ai/fastapi_v6/saved_models/model_meta_v6.json`

## DB 테이블
- `daily_sales`
- `daily_context`
- `inventory_snapshot`
- `feature_snapshot`
- `prediction_result`
- `training_dataset`
- `job_run`
