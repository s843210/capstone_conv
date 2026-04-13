# Spring 팀 연동 작업 TODO

기준 FastAPI 엔드포인트: `POST /api/v1/jobs/daily-run`
기준 날짜: 2026-04-13

## 1) 스케줄러
- 매일 17:50(KST) 스케줄러 추가
- 실행일 `D` 기준 예측일 `targetDate = D+1` 계산
- 실패 시 재시도 3회 + 알람 로그 남김

## 2) FastAPI 요청 데이터 생성
- `runDate`: 실행일(D)
- `targetDate`: 예측일(D+1)
- `salesHistory[]`: 상품별 판매이력(최소 최근 14일, `salesDate`, `pluCode`, `salesQty`)
- `items[]`: 상품/재고(`pluCode`, `productName`, `categoryL`, `categoryM`, `categoryS`, `currentStock`)
- `context`: `avgTempC`, `precipitationMm`, `isRain`, `isHoliday`, `academicEvent`, `buildingHeadcount`
- `dryRun`: 운영 기본 `false`

## 3) DB/조회 준비 (Spring 내부)
- 전날 확정 판매량을 조회할 수 있는 소스 준비
- 상품 마스터에 `pluCode`, `name`, `category` 정합성 보장
- 실행 시점 재고 스냅샷 조회 가능 상태 보장
- 컨텍스트(날씨/학사/휴일/유동) 일자별 조회 경로 확정

## 4) FastAPI 호출/응답 처리
- 요청 URL: `http://<fastapi-host>:8000/api/v1/jobs/daily-run`
- 타임아웃 10초 이상 설정
- 응답 필드 저장: `runId`, `status`, `predictedRows`, `springSavedCount`, `error`
- 실패 시 동일 `targetDate` 재실행 가능하도록 idempotent 처리

## 5) 기존 Spring API 유지
- `POST /api/ai/predictions`는 기존 DTO shape 유지
- FastAPI가 보내는 payload를 현재 저장 로직에서 수용 가능해야 함
- `savedCount`를 응답에 계속 포함

## 6) 검증 시나리오
- 정상 시나리오: 1회 호출로 `savedCount > 0`
- 부분 실패: 일부 PLU skip 시에도 전체 배치 실패하지 않음 확인
- 재실행: 같은 `targetDate` 재호출 시 중복 폭증 없이 upsert 확인
- 대시보드 반영: 저장 후 `/api/dashboard` 데이터 반영 확인

## 7) 수용 기준(DoD)
- 17:50 자동 실행 성공
- FastAPI `status=completed`
- Spring `savedCount` 정상 기록
- 다음날 재실행(동일 targetDate) 안정 동작
