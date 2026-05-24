# Technical Design: EC2 단일 서버 배포

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  AWS EC2 (Ubuntu 22.04, t3.medium)                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Nginx (port 80 → 443 redirect)                          │   │
│  │  - HTTPS (Let's Encrypt)                                  │   │
│  │  - Static: /var/www/coopsket → React SPA                 │   │
│  │  - Proxy: /api/* → http://127.0.0.1:8080                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│           │                              │                        │
│           ▼                              ▼                        │
│  ┌─────────────────┐          ┌─────────────────────┐           │
│  │  React SPA      │          │  Spring Boot         │           │
│  │  (정적 파일)     │          │  :8080 (127.0.0.1)   │           │
│  │  /var/www/       │          │  coopsket-backend    │           │
│  │  coopsket/       │          │  (systemd)           │           │
│  └─────────────────┘          └─────────┬───────────┘           │
│                                          │                        │
│                               ┌──────────┼──────────┐            │
│                               ▼                      ▼            │
│                    ┌──────────────────┐  ┌────────────────────┐  │
│                    │  PostgreSQL 15   │  │  AI FastAPI        │  │
│                    │  :5432           │  │  :8000             │  │
│                    │  (Docker)        │  │  (127.0.0.1)       │  │
│                    │  campus-store-db │  │  coopsket-ai       │  │
│                    │  volume: pgdata  │  │  (systemd)         │  │
│                    └──────────────────┘  └────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

외부 접근:
  - https://도메인       → Nginx → React SPA
  - https://도메인/api/* → Nginx → Spring Boot :8080

내부 전용 (외부 차단):
  - 127.0.0.1:8080  Spring Boot
  - 127.0.0.1:5432  PostgreSQL (Docker)
  - 127.0.0.1:8000  AI FastAPI
```

## Component Design

### 1. EC2 디렉토리 구조

```
/home/ubuntu/
└── capston_conv/                    ← git clone 위치
    ├── backend/conv/
    │   ├── .env                     ← 환경변수 (git 미포함, EC2에서만 생성)
    │   ├── docker-compose.yml       ← PostgreSQL 컨테이너 정의
    │   ├── gradlew
    │   └── build/libs/conv-0.0.1-SNAPSHOT.jar  ← 빌드 산출물
    ├── front/store-dashboard-frontend-main/
    │   ├── .env.production          ← VITE_API_BASE_URL 설정
    │   └── dist/                    ← 빌드 산출물
    ├── Ai/
    │   ├── .venv/                   ← Python 가상환경
    │   ├── requirements.txt
    │   ├── src/api_server.py        ← FastAPI 엔트리포인트
    │   └── outputs/models/          ← 학습된 모델 파일
    └── deploy/                      ← 배포 설정 파일 모음
        ├── nginx/coopsket           ← Nginx 설정
        ├── systemd/coopsket-backend.service
        ├── systemd/coopsket-ai.service
        ├── scripts/deploy.sh
        └── .env.example

/var/www/coopsket/                   ← Nginx가 서빙하는 정적 파일
/etc/nginx/sites-available/coopsket  ← Nginx 서버 블록
/etc/systemd/system/coopsket-backend.service
/etc/systemd/system/coopsket-ai.service
```

### 2. Docker Compose (PostgreSQL)

```yaml
# backend/conv/docker-compose.yml (수정 후)
version: '3.8'

services:
  db:
    image: postgres:15
    container_name: campus-store-db
    restart: unless-stopped
    ports:
      - "127.0.0.1:5432:5432"
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
      TZ: Asia/Seoul
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

변경점:
- `ports`: `"${DB_PORT}:5432"` → `"127.0.0.1:5432:5432"` (외부 접근 차단)
- `restart: unless-stopped` 추가

### 3. systemd 서비스: coopsket-backend

```ini
# deploy/systemd/coopsket-backend.service
[Unit]
Description=Coopsket Spring Backend
After=network.target docker.service
Requires=docker.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/capston_conv/backend/conv
EnvironmentFile=/home/ubuntu/capston_conv/backend/conv/.env
ExecStart=/usr/bin/java -jar /home/ubuntu/capston_conv/backend/conv/build/libs/conv-0.0.1-SNAPSHOT.jar
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 4. systemd 서비스: coopsket-ai

```ini
# deploy/systemd/coopsket-ai.service
[Unit]
Description=Coopsket AI FastAPI
After=network.target docker.service
Requires=docker.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/capston_conv/Ai
EnvironmentFile=/home/ubuntu/capston_conv/backend/conv/.env
ExecStart=/home/ubuntu/capston_conv/Ai/.venv/bin/python -m uvicorn src.api_server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5. Nginx 설정

```nginx
# deploy/nginx/coopsket
# Certbot 적용 전 초기 설정 (HTTP only)
server {
    listen 80;
    server_name 도메인;

    root /var/www/coopsket;
    index index.html;

    client_max_body_size 20M;

    # API 프록시
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Swagger UI 프록시
    location /swagger-ui/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }

    location /v3/api-docs/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Certbot 실행 후 자동으로 HTTPS 블록이 추가됨:
```bash
sudo certbot --nginx -d 도메인
```

### 6. 프론트엔드 빌드 환경변수

```env
# front/store-dashboard-frontend-main/.env.production
VITE_API_BASE_URL=https://도메인
```

### 7. CORS 수정 (WebConfig.java)

```java
// 배포 도메인 추가
.allowedOrigins(
    "http://localhost:5173",
    "http://localhost:8081",
    "http://localhost:19006",
    "http://10.63.213.230:8081",
    "http://10.63.213.230:19006",
    "https://도메인"          // ← 추가
)
```

### 8. 환경변수 파일 (.env.example)

```env
# deploy/.env.example
# 이 파일은 템플릿입니다. 실제 값을 넣어 backend/conv/.env로 복사하세요.

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=campus_store
DB_USER=postgres
DB_PASSWORD=여기에_강력한_비밀번호

# Admin Auth
ADMIN_LOGIN_ID=admin
ADMIN_PASSWORD=여기에_관리자_비밀번호
ADMIN_NAME=관리자
ADMIN_EMAIL=admin@campus-store.local

# JWT
JWT_SECRET=여기에_충분히_긴_랜덤_문자열
JWT_ISSUER=campus-store
JWT_EXPIRATION_MINUTES=120

# Google OAuth
GOOGLE_CLIENT_IDS=WEB_CLIENT_ID,ANDROID_CLIENT_ID
GOOGLE_ALLOWED_DOMAIN=

# AI
AI_BASE_URL=http://127.0.0.1:8000

# Weather
WEATHER_ENABLED=false
WEATHER_API_KEY=
WEATHER_LAT=37.2941
WEATHER_LON=127.0448
```

## Network Flow

```
[사용자 브라우저]
       │
       ▼ HTTPS (443)
[Nginx - SSL termination]
       │
       ├── GET /            → /var/www/coopsket/index.html (React SPA)
       ├── GET /assets/*    → /var/www/coopsket/assets/* (정적 파일)
       └── ANY /api/*       → proxy_pass http://127.0.0.1:8080
                                    │
                                    ▼
                            [Spring Boot :8080]
                                    │
                         ┌──────────┼──────────┐
                         ▼                      ▼
              [PostgreSQL :5432]      [FastAPI :8000]
              (Docker container)      (AI 예측 호출)
```

## Deployment Sequence

```
1. EC2 접속 (SSH)
2. 기본 패키지 설치
3. 레포 클론 + git lfs pull
4. .env 파일 생성
5. Docker PostgreSQL 실행
6. Spring Boot 빌드 + systemd 등록
7. AI FastAPI venv 설정 + systemd 등록
8. 프론트엔드 빌드 + Nginx 정적 파일 배치
9. Nginx 설정 + 서비스 시작
10. Certbot으로 HTTPS 발급
11. 배포 후 검증
12. 초기 데이터 적재
```

## Security Design

| 항목 | 설계 |
|------|------|
| 외부 포트 | 22 (SSH), 80 (→443 redirect), 443 (HTTPS) |
| 내부 전용 | 8080 (Spring), 5432 (PostgreSQL), 8000 (FastAPI) |
| SSL | Let's Encrypt, 자동 갱신 |
| 환경변수 | .env 파일 권한 600, git 미포함 |
| DB 접근 | 127.0.0.1 바인딩으로 외부 차단 |
| CORS | 배포 도메인만 허용 |
| JWT | 운영용 강력한 시크릿 사용 |

## Rollback Strategy

| 상황 | 대응 |
|------|------|
| 백엔드 배포 실패 | 이전 JAR 파일로 ExecStart 경로 변경 후 systemctl restart |
| 프론트 배포 실패 | 이전 dist/ 백업에서 rsync 복원 |
| DB 마이그레이션 실패 | Flyway repair 또는 수동 SQL 롤백 |
| 전체 롤백 | git checkout으로 이전 커밋 복원 후 재빌드 |
