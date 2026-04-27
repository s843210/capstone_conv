# Weather Context Contract (Spring)

## 목적
- `daily_context` 테이블에 예측 대상일(`target_date`) 기준 컨텍스트를 누적 저장한다.
- 초기 범위는 날씨(`avg_temp_c`, `precipitation_mm`, `is_rain`) 적재다.
- `is_holiday`, `academic_event`, `building_headcount`는 기존값 유지(없으면 0 기본값).

## 컬럼 매핑
- `target_date`: 적재 기준일 (YYYY-MM-DD)
- `avg_temp_c`: 해당일 평균 기온(섭씨)
- `precipitation_mm`: 해당일 강수량 합(mm)
- `is_rain`: 강수량 > 0 이면 1, 아니면 0
- `is_holiday`: 기본 0
- `academic_event`: 기본 0
- `building_headcount`: 기본 0

## 실행 API
### 1) 단건 적재
- `POST /api/admin/context/weather?targetDate=YYYY-MM-DD`
- `targetDate` 미지정 시: KST 기준 내일 날짜 사용
- `dryRun=true`면 DB 저장 없이 조회만 수행

### 2) 기간 백필
- `POST /api/admin/context/weather/backfill?from=YYYY-MM-DD&to=YYYY-MM-DD&maxDays=365`
- 범위 내 날짜를 순차 적재
- 실패 건은 응답 `errors`에 일부 포함

## 스케줄
- 기본 크론: `0 40 17 * * *` (KST)
- `WEATHER_ENABLED=true`일 때만 스케줄 동작

## 환경변수
- `WEATHER_ENABLED`
- `WEATHER_BASE_URL`
- `WEATHER_FORECAST_PATH`
- `WEATHER_API_KEY` (기본 빈값)
- `WEATHER_LAT`, `WEATHER_LON`
- `WEATHER_TIMEOUT_SEC`
- `WEATHER_RETRY`
- `WEATHER_RETRY_BACKOFF_MS`
- `WEATHER_SCHEDULE_CRON`
- `WEATHER_SCHEDULE_ZONE`

## 실패/재시도
- API 호출 실패 시 최대 `WEATHER_RETRY` 횟수만큼 지수 백오프 재시도
- 최종 실패 시 예외 로그를 남기고 작업 실패 처리
