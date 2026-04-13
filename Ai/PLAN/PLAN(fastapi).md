# FastAPI 설계 자동생성용 Prompt MD 작성안

## Summary
- 목표: 다른 LLM에 이 프롬프트만 주면, 네 프로젝트 기준으로 **FastAPI 연동 설계 문서(plan.md)**를 바로 만들게 한다.
- 범위: 모델 알고리즘 설계 제외, **FastAPI 서비스 설계/연동/운영 계획만** 포함.
- 연동 방향 고정: **FastAPI → Spring `POST /api/ai/predictions`**.

## Prompt MD (그대로 복붙)
```md
# 프로젝트 설계 요청서 (FastAPI 연동 전용)

너는 시니어 백엔드 아키텍트다.  
아래 컨텍스트를 기준으로, 이 프로젝트의 **FastAPI 설계 계획서(plan.md)**를 작성하라.  
목표는 팀원이 바로 구현 시작할 수 있는 수준의 결정 완료 문서다.

## 1) 절대 조건
- AI 모델 알고리즘 설계는 제외한다. (랜덤포레스트 자체 튜닝/학습전략 상세 제외)
- FastAPI 서비스 설계, 데이터흐름, API 계약, 배치/운영/장애대응만 다룬다.
- 문서는 한국어로 작성한다.
- 모호한 부분은 합리적 기본값을 선택하고 `가정(Assumptions)`에 명시한다.

## 2) 현재 시스템 컨텍스트
- Spring 서버는 AI 결과 수신 API를 이미 가지고 있다.
- 연동 방향은 `FastAPI -> Spring` push 방식으로 고정한다.
- Spring 수신 엔드포인트: `POST /api/ai/predictions`
- Spring 요청 스키마(핵심):
  - `targetDate: LocalDate`
  - `categories[]`
    - `categoryName: String`
    - `totalRecommendedOrder: int`
    - `aiMessage: String`
    - `products[]`
      - `pluCode: String`
      - `predictedSales: int`
      - `recommendedOrder: int`
      - `confidenceScore: Double`
- 단일 매장 기준으로 진행한다. (`store_id` 생략)
- 현재 재고(`current_stock`)는 모델 입력이 아니라, 발주 계산 단계에서 사용하는 정책 변수로 취급한다.
- Feature 컬럼 계열(참고): `lag_1, lag_3, lag_7, rolling_7_mean, rolling_7_std, day_of_week, month, is_holiday, academic_event, building_headcount ...`

## 3) 문서 산출 형식 (반드시 이 순서)
1. **요약(1문단)**  
2. **아키텍처 설계**  
   - FastAPI 내부 모듈 분리 (예: feature_builder, inference_service, order_policy, spring_client, scheduler)
   - 모듈별 책임과 I/O
3. **API/인터페이스 계약**  
   - FastAPI 내부 운영용 API 제안 (`/health`, `/jobs/predict`, 필요시 `/jobs/status/{id}`)
   - Spring 전송 payload 예시(JSON)
   - 필수/선택 필드 구분
4. **데이터 흐름 (E2E)**  
   - 입력 수집 -> 피처 생성 -> 추론 -> 권장발주 계산 -> Spring 전송 -> 로깅
5. **배치/운영 계획**  
   - 일 1회 실행 기준 스케줄
   - 재시도 정책, 타임아웃, idempotency(동일 targetDate 재실행)
   - 실패 시 보관할 로그 필드
6. **검증/테스트 계획**  
   - 단위 테스트, 통합 테스트, 계약 테스트
   - 최소 수용 기준(DoD)
7. **릴리즈 계획**  
   - 로컬 -> 스테이징 -> 운영 단계
   - 롤백 전략
8. **리스크 & 질문 리스트**  
   - 팀장/백엔드/AI팀에 확인할 결정 포인트를 우선순위로 정리
9. **즉시 실행 가능한 TODO 체크리스트**  
   - 담당 역할별(백엔드/AI/인프라) 1~2주 작업 항목

## 4) 품질 기준
- 구현자가 추가 의사결정 없이 시작 가능해야 한다.
- 추상적인 문장 대신, 엔드포인트/필드/실패 처리 기준을 명확히 쓴다.
- 과한 이론 설명 없이 실무 실행 중심으로 작성한다.

## 5) 출력 형식
- 최종 출력은 Markdown 한 파일 형식으로만 제공한다.
- 문서 제목은: `# FastAPI Integration Plan v1`
```

## Test Plan
- 이 프롬프트를 다른 LLM에 넣었을 때 아래가 나오면 통과:
  - `FastAPI -> Spring` 고정 방향이 유지됨
  - `/api/ai/predictions` payload가 DTO 구조와 일치함
  - 스케줄/재시도/로그/재실행(idempotency) 기준 포함
  - 구현 TODO가 역할별로 분리됨

## Assumptions
- 네가 원하는 결과물은 “실행 가능한 설계문서 자동생성 프롬프트”이며, 코드 생성 프롬프트가 아님.
- 현재 기준 API 계약은 Spring 수신 DTO를 우선으로 삼음.
