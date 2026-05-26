# COOPSKET

조선대학교 교내 편의점 운영을 위한 AI 기반 재고·발주 추천 및 학생 요청 관리 시스템입니다.

관리자 웹 대시보드에서는 상품/재고/판매 데이터 업로드, AI 예측 실행, 발주 추천 확인, 학생 요청·건의사항 관리를 수행합니다. 학생 앱에서는 Google OAuth 로그인 후 원하는 상품 요청과 건의사항 등록을 할 수 있습니다.

## 주요 기능

- 관리자 JWT 로그인
- 학생 Google OAuth 로그인
- 상품 마스터, 재고, 판매 데이터 업로드
- 월별 판매 데이터 기반 AI 수요 예측
- 예측 판매량 기반 발주 추천
- 재고 현황 및 판매량 순위 대시보드
- 학생 상품 요청 관리
- 학생 건의사항 등록/조회/삭제
- EC2 + Nginx + GitHub Actions 기반 자동 배포

## 전체 구조

```text
CAP/
├── Ai/                         # AI 수요예측 파이프라인 및 FastAPI 서버
├── App/                        # 학생용 Expo React Native 앱
├── backend/conv/               # Spring Boot 백엔드 API 서버
├── front/store-dashboard-frontend-main/
│   └── src/                    # 관리자용 React/Vite 웹 대시보드
├── deploy/                     # EC2 배포 스크립트, nginx, systemd 설정
├── docs/                       # 프로젝트 설명 문서
├── outputs/                    # 로컬 실행 로그/리포트 산출물
├── .github/workflows/          # GitHub Actions CI/CD 설정
└── README.md
```

## 서비스 아키텍처

```text
학생 앱 Expo/React Native
  └─ Google OAuth 로그인
  └─ 학생 요청/건의사항 API 호출

관리자 웹 React/Vite
  └─ 관리자 로그인
  └─ 대시보드, 재고, 발주 추천, 데이터 업로드

Spring Boot Backend
  └─ JWT 인증/인가
  └─ PostgreSQL 데이터 관리
  └─ AI FastAPI 호출

AI FastAPI
  └─ 판매 데이터 기반 예측 실행
  └─ 발주 추천 결과 생성

PostgreSQL
  └─ 상품, 재고, 판매, 예측, 학생 요청, 건의사항 저장
```

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 관리자 웹 | React, Vite, Chart.js, React Router |
| 학생 앱 | Expo, React Native, React Navigation, Google Sign-In |
| 백엔드 | Java 17, Spring Boot 3, Spring Security, JPA, Flyway, QueryDSL |
| 인증 | JWT, Google OAuth ID Token 검증 |
| DB | PostgreSQL 15 |
| AI | Python, FastAPI, pandas, scikit-learn, LightGBM |
| 배포 | EC2, Nginx, systemd, GitHub Actions, Git LFS |

## 모듈별 역할

### `backend/conv`

Spring Boot API 서버입니다.

주요 역할:

- 관리자/학생 인증 및 JWT 발급
- Google ID Token 검증
- 상품 마스터, 재고, 판매 데이터 적재
- 대시보드 통계 조회
- AI 예측 실행 요청
- 발주 추천 결과 조회
- 학생 상품 요청 및 건의사항 API 제공

주요 API:

```text
POST /api/auth/admin/login
POST /api/auth/google
GET  /api/auth/me

GET  /api/dashboard
GET  /api/inventory
POST /api/admin/products/master/upload
POST /api/admin/inventory/upload
POST /api/admin/sales/upload
POST /api/admin/sales/monthly-v2/import-processed

POST /api/admin/ai/predict
POST /api/ai/predictions

GET  /api/student/products
GET  /api/student/requests
POST /api/student/requests
GET  /api/student/suggestions
POST /api/student/suggestions
```

### `front/store-dashboard-frontend-main`

관리자 웹 대시보드입니다.

주요 화면:

- 로그인
- 대시보드
- 재고 관리
- 발주 추천
- 학생 신청 관리
- 건의사항
- 데이터 업로드/AI 실행 패널

운영 API 주소는 `.env.production`의 `VITE_API_BASE_URL`로 관리합니다.

### `App/app_fronted23/InventoryRequestApp`

학생용 모바일 앱입니다.

주요 기능:

- Google 로그인
- 상품 목록 조회
- 상품 신청
- 내 신청 목록 조회/삭제
- 건의사항 등록/조회/삭제

앱에서 사용하는 Google Client ID는 `.env.local` 또는 EAS env의 `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`, `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID`로 관리합니다.

### `Ai`

AI 수요예측 파이프라인과 FastAPI 서버입니다.

주요 역할:

- 월별 판매 데이터 전처리
- 학사일정, 시간표, 날씨 데이터 병합
- 수요예측 모델 학습/추론
- 발주 추천량 계산
- Spring Boot 백엔드와 FastAPI로 연동

Git LFS 관리 대상:

```text
Ai/data/processed/model_features_monthly_v2.csv
Ai/data/processed/monthly_sales_with_calendar_timetable_weather_v2.csv
Ai/data/processed/monthly_sales_daily_filled_v2_clean.csv
Ai/outputs/models/random_forest_monthly_v2_model.pkl
```

## 로컬 실행 순서

### 1. 백엔드 환경변수 준비

```bash
cd backend/conv
cp .env.example .env
```

`.env`에 실제 DB, JWT, 관리자 계정, Google OAuth 값을 입력합니다.

필수 값:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=campus_store
DB_USER=postgres
DB_PASSWORD=postgres

ADMIN_LOGIN_ID=admin
ADMIN_PASSWORD=admin1234
JWT_SECRET=change-this-to-a-long-random-secret
JWT_ISSUER=campus-store
JWT_EXPIRATION_MINUTES=120

GOOGLE_CLIENT_IDS=웹클라이언트ID,안드로이드클라이언트ID
AI_BASE_URL=http://127.0.0.1:8000
```

### 2. PostgreSQL 실행

```bash
cd backend/conv
docker compose up -d db
```

### 3. Spring Boot 백엔드 실행

```bash
cd backend/conv
./gradlew bootRun
```

백엔드 기본 주소:

```text
http://127.0.0.1:8080
```

인증 확인:

```bash
curl http://127.0.0.1:8080/api/auth/me
```

`401 인증이 필요합니다`가 나오면 서버는 정상입니다.

### 4. AI FastAPI 실행

```bash
cd Ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api_server:app --host 127.0.0.1 --port 8000 --reload
```

AI 서버 기본 주소:

```text
http://127.0.0.1:8000
```

### 5. 관리자 웹 실행

```bash
cd front/store-dashboard-frontend-main
npm ci
npm run dev
```

웹 기본 주소:

```text
http://127.0.0.1:5173
```

### 6. 학생 앱 실행

```bash
cd App/app_fronted23/InventoryRequestApp
npm install
npx expo start
```

개발 빌드 또는 APK 테스트가 필요하면 EAS를 사용합니다.

```bash
npx eas-cli@latest build -p android --profile preview
npx eas-cli@latest build -p android --profile production
```

## 데이터 적재 순서

초기 DB 구성 후 관리자 웹 또는 API로 아래 순서대로 데이터를 넣습니다.

1. 상품 마스터 업로드
2. 재고 데이터 업로드
3. 판매 데이터 업로드
4. 월별 AI 학습용 processed CSV 적재
5. AI 예측 실행
6. 발주 추천 결과 확인

월별 processed CSV:

```text
Ai/data/processed/monthly_sales_with_calendar_timetable_weather_v2.csv
```

이 파일은 Git LFS 대상입니다.

## 인증 흐름

학생 앱 로그인 흐름:

```text
학생 앱
-> Google 로그인
-> Google ID Token 발급
-> 백엔드 /api/auth/google 전송
-> 백엔드가 Google 토큰 검증
-> app_user 조회 또는 생성
-> JWT 발급
-> 앱이 JWT 저장
-> 이후 API 요청에 Authorization: Bearer <token> 사용
```

자세한 설명:

```text
docs/backend-auth-flow.md
```

## 배포 구조

운영 주소:

```text
https://coop1925.duckdns.org
```

배포 구성:

- Nginx: 정적 웹 파일 서빙 및 API 프록시
- Spring Boot: `coopsket-backend` systemd 서비스
- AI FastAPI: `coopsket-ai` systemd 서비스
- PostgreSQL: Docker Compose DB 컨테이너
- GitHub Actions: EC2 SSH 배포 자동화

현재 GitHub Actions 배포 트리거:

```text
main 브랜치 push
```

워크플로우:

```text
.github/workflows/deploy.yml
```

배포 시 수행 작업:

1. EC2에서 코드 pull
2. Git LFS 파일 pull
3. Spring Boot 빌드 후 `coopsket-backend` 재시작
4. AI 의존성 설치 후 `coopsket-ai` 재시작
5. React 웹 빌드
6. Nginx 정적 파일 교체 및 reload

## 주요 환경변수 파일

| 위치 | 용도 | Git 포함 여부 |
| --- | --- | --- |
| `backend/conv/.env` | DB, JWT, 관리자 계정, Google OAuth, 외부 API | 제외 |
| `backend/conv/.env.example` | 백엔드 env 예시 | 포함 |
| `front/store-dashboard-frontend-main/.env.production` | 운영 웹 API 주소 | 포함 |
| `App/app_fronted23/InventoryRequestApp/.env.local` | 앱 Google Client ID | 제외 |
| EAS env | 앱 빌드 서버용 Google Client ID | Git 외부 관리 |

## 참고 문서

```text
Ai/README.md
Ai/PIPELINE_USAGE.md
MVP_DAILY_OPERATION_GUIDE.md
docs/backend-auth-flow.md
deploy/scripts/deploy.sh
```

## 주의사항

- `.env`, `.env.local`, 키 파일, 실제 비밀번호는 커밋하지 않습니다.
- 대용량 AI 데이터와 모델은 Git LFS로 관리합니다.
- 로컬 DB 컨테이너를 삭제하면 데이터가 사라질 수 있으므로 일반 종료는 `docker compose stop db`를 사용합니다.
- 운영 백엔드에서 Google 로그인을 사용하려면 EC2의 `backend/conv/.env`에 `GOOGLE_CLIENT_IDS`가 반드시 있어야 합니다.
- Play Store 배포 앱은 Play App Signing SHA-1을 Google Cloud Android OAuth Client에 추가해야 Google 로그인이 정상 동작합니다.
