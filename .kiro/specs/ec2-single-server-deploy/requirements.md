# Requirements Document

## Introduction

캠퍼스 편의점 관리 시스템(Campus Store Management System)을 AWS EC2 단일 서버에 배포하기 위한 요구사항을 정의한다. 배포 아키텍처는 Ubuntu EC2 인스턴스 위에 Docker PostgreSQL, Spring Boot 백엔드, AI FastAPI 서버, Nginx 리버스 프록시 + 정적 프론트엔드 서빙으로 구성되며, Let's Encrypt를 통한 HTTPS를 적용한다.

## Glossary

- **EC2_Instance**: AWS EC2 Ubuntu 서버 인스턴스
- **Docker_PostgreSQL**: EC2 내부에서 Docker 컨테이너로 실행되는 PostgreSQL 15 데이터베이스
- **Spring_Boot_Backend**: Java 17 기반 Spring Boot 3.5 백엔드 애플리케이션 (포트 8080)
- **AI_FastAPI**: Python 기반 AI 예측 서버, uvicorn으로 127.0.0.1:8000에서 실행
- **Nginx**: 리버스 프록시 및 정적 파일 서빙을 담당하는 웹 서버
- **Vite_React_Frontend**: React 19 + Vite 8 기반 관리자 대시보드 프론트엔드
- **Certbot**: Let's Encrypt SSL 인증서 발급 및 자동 갱신 도구
- **Security_Group**: EC2 인스턴스에 적용되는 AWS 네트워크 방화벽 규칙
- **Env_File**: 환경변수를 저장하는 파일 (.env), 버전 관리에 포함하지 않음
- **Deploy_Domain**: 외부 접속에 사용되는 도메인 주소

## Requirements

### Requirement 1: EC2 인프라 프로비저닝

**User Story:** As a 시스템 관리자, I want EC2 인스턴스를 적절한 사양으로 프로비저닝하고 싶다, so that 캠퍼스 편의점 시스템의 모든 컴포넌트를 안정적으로 운영할 수 있다.

#### Acceptance Criteria

1. THE EC2_Instance SHALL run Ubuntu 22.04 LTS or later as the operating system
2. THE EC2_Instance SHALL have a minimum of 2 vCPU and 4GB RAM (t3.medium or equivalent)
3. THE EC2_Instance SHALL have a minimum of 30GB EBS storage volume attached
4. THE EC2_Instance SHALL have Docker Engine and Docker Compose plugin installed
5. THE EC2_Instance SHALL have Java 17 (OpenJDK) installed
6. THE EC2_Instance SHALL have Node.js 22.x and npm installed for frontend build
7. THE EC2_Instance SHALL have Nginx installed as a system service
8. THE EC2_Instance SHALL have Certbot installed with the Nginx plugin
9. THE EC2_Instance SHALL have Python 3, python3-venv, and python3-pip installed for AI FastAPI
10. THE EC2_Instance SHALL have git and git-lfs installed for repository cloning

### Requirement 2: Security Group 네트워크 규칙

**User Story:** As a 시스템 관리자, I want 최소한의 포트만 외부에 노출하고 싶다, so that 불필요한 공격 표면을 줄이고 시스템을 보호할 수 있다.

#### Acceptance Criteria

1. THE Security_Group SHALL allow inbound TCP traffic on port 22 (SSH) from authorized IP ranges only
2. THE Security_Group SHALL allow inbound TCP traffic on port 80 (HTTP) from all sources (0.0.0.0/0)
3. THE Security_Group SHALL allow inbound TCP traffic on port 443 (HTTPS) from all sources (0.0.0.0/0)
4. THE Security_Group SHALL deny inbound TCP traffic on port 8080 from all external sources
5. THE Security_Group SHALL deny inbound TCP traffic on port 5432 from all external sources
6. THE Security_Group SHALL deny inbound TCP traffic on port 8000 from all external sources (AI FastAPI는 내부 전용)
7. THE Security_Group SHALL allow all outbound traffic for system updates and external API calls

### Requirement 3: Docker PostgreSQL 데이터베이스

**User Story:** As a 시스템 관리자, I want PostgreSQL을 Docker 컨테이너로 실행하고 싶다, so that 데이터베이스를 격리된 환경에서 관리하고 데이터 영속성을 보장할 수 있다.

#### Acceptance Criteria

1. THE Docker_PostgreSQL SHALL run PostgreSQL 15 image inside a Docker container named campus-store-db
2. THE Docker_PostgreSQL SHALL bind to 127.0.0.1:5432 only, preventing external network access
3. THE Docker_PostgreSQL SHALL use a named Docker volume (pgdata) for data persistence
4. THE Docker_PostgreSQL SHALL read database credentials from the Env_File (DB_USER, DB_PASSWORD, DB_NAME)
5. THE Docker_PostgreSQL SHALL set timezone to Asia/Seoul
6. THE Docker_PostgreSQL SHALL restart automatically on system reboot (restart policy: unless-stopped)
7. WHEN the Docker container is recreated, THE Docker_PostgreSQL SHALL retain all existing data through the named volume
8. WHEN `docker compose down` is executed (without -v flag), THE data SHALL be preserved

### Requirement 4: Spring Boot 백엔드 배포

**User Story:** As a 시스템 관리자, I want Spring Boot 애플리케이션을 EC2에서 안정적으로 실행하고 싶다, so that API 서비스를 지속적으로 제공할 수 있다.

#### Acceptance Criteria

1. THE Spring_Boot_Backend SHALL be built using `./gradlew clean build -x test` producing an executable JAR
2. THE Spring_Boot_Backend SHALL run on port 8080 bound to 127.0.0.1 only
3. THE Spring_Boot_Backend SHALL read all configuration from environment variables defined in the Env_File
4. THE Spring_Boot_Backend SHALL connect to Docker_PostgreSQL at 127.0.0.1:5432
5. THE Spring_Boot_Backend SHALL run as a systemd service (coopsket-backend) for automatic restart and log management
6. WHEN the Spring_Boot_Backend process crashes, THE systemd service SHALL restart it automatically within 5 seconds
7. THE Spring_Boot_Backend SHALL execute Flyway migrations on startup to ensure database schema is current
8. THE Spring_Boot_Backend SHALL include the Deploy_Domain in CORS allowed origins
9. THE systemd service SHALL depend on docker.service to ensure DB is available before backend starts

### Requirement 5: AI FastAPI 서버 배포

**User Story:** As a 시스템 관리자, I want AI 예측 서버를 EC2에서 실행하고 싶다, so that 백엔드가 AI 예측 기능을 내부적으로 호출할 수 있다.

#### Acceptance Criteria

1. THE AI_FastAPI SHALL run inside a Python virtual environment (.venv) created in the Ai/ directory
2. THE AI_FastAPI SHALL install dependencies from Ai/requirements.txt
3. THE AI_FastAPI SHALL bind to 127.0.0.1:8000 only, preventing external network access
4. THE AI_FastAPI SHALL run as a systemd service (coopsket-ai) for automatic restart and log management
5. WHEN the AI_FastAPI process crashes, THE systemd service SHALL restart it automatically within 5 seconds
6. THE AI_FastAPI SHALL require the trained model file (Ai/outputs/models/random_forest_monthly_v2_model.pkl) to be present
7. THE Spring_Boot_Backend SHALL connect to AI_FastAPI at http://127.0.0.1:8000 via the AI_BASE_URL environment variable
8. THE coopsket-ai systemd service SHALL load environment variables from the same Env_File as the backend

### Requirement 6: Vite React 프론트엔드 빌드 및 서빙

**User Story:** As a 시스템 관리자, I want 프론트엔드를 빌드하여 Nginx로 정적 서빙하고 싶다, so that 사용자가 빠르고 안정적으로 대시보드에 접근할 수 있다.

#### Acceptance Criteria

1. THE Vite_React_Frontend SHALL be built using `npm ci && npm run build` with VITE_API_BASE_URL environment variable set to https://Deploy_Domain
2. THE Vite_React_Frontend SHALL produce static files in the dist/ directory
3. THE dist/ contents SHALL be copied to /var/www/coopsket using `sudo rsync -a --delete dist/ /var/www/coopsket/`
4. THE Nginx SHALL serve the Vite_React_Frontend static files from /var/www/coopsket
5. WHEN a request path does not match a static file, THE Nginx SHALL return index.html for client-side routing (SPA fallback)
6. THE Nginx SHALL set appropriate cache headers for static assets (CSS, JS, images)

### Requirement 7: Nginx 리버스 프록시 설정

**User Story:** As a 시스템 관리자, I want Nginx가 리버스 프록시 역할을 수행하도록 설정하고 싶다, so that 외부 요청을 적절한 내부 서비스로 라우팅할 수 있다.

#### Acceptance Criteria

1. THE Nginx SHALL listen on port 80 and redirect all HTTP requests to HTTPS (port 443)
2. THE Nginx SHALL listen on port 443 with SSL/TLS enabled
3. WHEN a request path starts with /api, THE Nginx SHALL proxy the request to http://127.0.0.1:8080
4. THE Nginx SHALL pass X-Real-IP, X-Forwarded-For, X-Forwarded-Proto headers to the Spring_Boot_Backend
5. THE Nginx SHALL serve the Deploy_Domain as the server_name
6. WHEN a request path does not start with /api, THE Nginx SHALL serve static files from /var/www/coopsket with try_files $uri $uri/ /index.html
7. THE Nginx SHALL set client_max_body_size to 20MB to match Spring Boot multipart upload limit
8. THE Nginx config SHALL be placed at /etc/nginx/sites-available/coopsket and symlinked to sites-enabled

### Requirement 8: HTTPS/SSL 인증서 관리

**User Story:** As a 시스템 관리자, I want Let's Encrypt를 통해 HTTPS를 적용하고 싶다, so that 사용자와 서버 간 통신이 암호화되어 보안을 확보할 수 있다.

#### Acceptance Criteria

1. THE Certbot SHALL obtain an SSL certificate for the Deploy_Domain from Let's Encrypt
2. THE Certbot SHALL configure Nginx to use the obtained SSL certificate automatically
3. THE Certbot SHALL set up automatic certificate renewal via systemd timer or cron
4. WHEN the SSL certificate is within 30 days of expiration, THE Certbot SHALL renew it automatically
5. IF certificate renewal fails, THEN THE Certbot SHALL retry and log the failure for administrator review

### Requirement 9: 환경변수 및 시크릿 관리

**User Story:** As a 시스템 관리자, I want 모든 민감 정보를 환경변수로 관리하고 싶다, so that 시크릿이 소스 코드에 노출되지 않고 안전하게 관리된다.

#### Acceptance Criteria

1. THE Env_File SHALL be located at /home/ubuntu/capston_conv/backend/conv/.env on the EC2_Instance
2. THE Env_File SHALL have file permissions set to 600 (owner read/write only)
3. THE Env_File SHALL NOT be committed to version control
4. THE Spring_Boot_Backend systemd service SHALL load environment variables from the Env_File via EnvironmentFile directive
5. THE AI_FastAPI systemd service SHALL also load environment variables from the same Env_File
6. THE Docker_PostgreSQL SHALL load database credentials from the Env_File via shell environment (set -a; source .env; set +a before docker compose up)

### Requirement 10: 코드 수정 필요 항목

**User Story:** As a 개발자, I want 배포 전 수정이 필요한 코드 항목을 명확히 파악하고 싶다, so that 배포 환경에서 정상 동작하도록 준비할 수 있다.

#### Acceptance Criteria

1. THE Spring_Boot_Backend SHALL have WebConfig.java modified to include the Deploy_Domain (https://Deploy_Domain) in CORS allowedOrigins
2. THE Spring_Boot_Backend SHALL have docker-compose.yml modified to bind PostgreSQL port to 127.0.0.1 only (127.0.0.1:5432:5432 instead of ${DB_PORT}:5432)
3. THE Spring_Boot_Backend SHALL have docker-compose.yml modified to add restart policy (restart: unless-stopped)
4. THE Vite_React_Frontend SHALL have .env.production created with VITE_API_BASE_URL set to https://Deploy_Domain

### Requirement 11: 초기 데이터 적재

**User Story:** As a 시스템 관리자, I want 배포 후 초기 데이터를 적재하는 절차를 알고 싶다, so that 시스템이 정상적으로 동작할 수 있다.

#### Acceptance Criteria

1. WHEN the database is first created, Flyway SHALL create all required tables automatically
2. AFTER tables are created, THE 관리자 SHALL upload product/inventory data via the web dashboard
3. AFTER product data is loaded, THE 관리자 SHALL upload daily sales data via the web dashboard
4. AFTER sales data is loaded, THE 관리자 SHALL trigger AI prediction via the dashboard button
5. IF a database dump (backup.sql) exists, IT SHALL be restorable via `cat backup.sql | docker exec -i campus-store-db psql -U postgres -d campus_store`

### Requirement 12: 배포 후 검증

**User Story:** As a 시스템 관리자, I want 배포 후 시스템이 정상 동작하는지 검증하고 싶다, so that 서비스 장애 없이 운영을 시작할 수 있다.

#### Acceptance Criteria

1. WHEN deployment is complete, THE EC2_Instance SHALL respond to HTTPS requests at https://Deploy_Domain with HTTP 200
2. WHEN deployment is complete, THE Nginx SHALL serve the Vite_React_Frontend index.html at https://Deploy_Domain/
3. WHEN deployment is complete, THE Nginx SHALL proxy API requests and https://Deploy_Domain/api/auth/me SHALL return 401 (서버 정상 동작 확인)
4. WHEN deployment is complete, THE Docker_PostgreSQL SHALL accept connections from Spring_Boot_Backend on 127.0.0.1:5432
5. WHEN deployment is complete, THE Certbot SHALL report a valid SSL certificate with more than 60 days until expiration
6. WHEN deployment is complete, THE Spring_Boot_Backend systemd service (coopsket-backend) SHALL report active (running) status
7. WHEN deployment is complete, THE AI_FastAPI systemd service (coopsket-ai) SHALL report active (running) status
8. WHEN deployment is complete, curl http://127.0.0.1:8000/health SHALL return a successful response
9. WHEN deployment is complete, THE Docker_PostgreSQL container (campus-store-db) SHALL report healthy status

---

## 환경변수 목록 (변수명만)

아래는 EC2 서버의 Env_File (`/home/ubuntu/capston_conv/backend/conv/.env`)에 포함되어야 하는 환경변수 목록이다. 실제 값은 보안상 기재하지 않는다.

| 변수명 | 용도 | 비고 |
|--------|------|------|
| DB_HOST | PostgreSQL 호스트 | localhost |
| DB_PORT | PostgreSQL 포트 | 5432 |
| DB_NAME | 데이터베이스 이름 | |
| DB_USER | 데이터베이스 사용자명 | |
| DB_PASSWORD | 데이터베이스 비밀번호 | 운영용 강력한 값 사용 |
| ADMIN_LOGIN_ID | 관리자 로그인 ID | |
| ADMIN_PASSWORD | 관리자 비밀번호 | |
| ADMIN_NAME | 관리자 이름 | |
| ADMIN_EMAIL | 관리자 이메일 | |
| JWT_SECRET | JWT 서명 시크릿 | 충분히 긴 랜덤 문자열 |
| JWT_ISSUER | JWT 발급자 | |
| JWT_EXPIRATION_MINUTES | JWT 만료 시간 (분) | |
| GOOGLE_CLIENT_IDS | Google OAuth 클라이언트 ID | Web,Android 쉼표 구분 |
| GOOGLE_ALLOWED_DOMAIN | Google OAuth 허용 도메인 | 빈 값 가능 |
| AI_BASE_URL | AI FastAPI 서버 URL | http://127.0.0.1:8000 |
| WEATHER_ENABLED | 날씨 API 활성화 여부 | true/false |
| WEATHER_API_KEY | OpenWeatherMap API 키 | |
| WEATHER_LAT | 날씨 조회 위도 | |
| WEATHER_LON | 날씨 조회 경도 | |

## 코드 수정 대상 파일 목록

| 파일 경로 | 수정 이유 |
|-----------|-----------|
| backend/conv/src/main/java/com/errorzero/conv/config/WebConfig.java | CORS allowedOrigins에 배포 도메인(https://도메인) 추가 필요 (현재 localhost만 허용) |
| backend/conv/docker-compose.yml | PostgreSQL 포트 바인딩을 127.0.0.1로 제한, restart 정책 추가 |

## 신규 생성 파일 목록

| 파일 경로 | 용도 |
|-----------|------|
| front/store-dashboard-frontend-main/.env.production | VITE_API_BASE_URL을 배포 도메인으로 설정 |
| deploy/nginx/coopsket | Nginx 서버 블록 설정 (리버스 프록시 + 정적 서빙 + HTTPS) |
| deploy/systemd/coopsket-backend.service | Spring Boot systemd 서비스 유닛 파일 |
| deploy/systemd/coopsket-ai.service | AI FastAPI systemd 서비스 유닛 파일 |
| deploy/scripts/deploy.sh | 배포 자동화 스크립트 |
| deploy/.env.example | 환경변수 템플릿 (실제 값 없이 변수명만) |

## 자주 발생하는 문제 (Troubleshooting)

| 증상 | 원인 및 해결 |
|------|-------------|
| 웹은 뜨는데 API 호출 실패 | VITE_API_BASE_URL 확인, Spring CORS에 도메인 추가 확인 |
| AI 예측 실행 실패 | coopsket-ai 서비스 상태 확인, AI_BASE_URL=http://127.0.0.1:8000 확인, 모델 파일 존재 확인 |
| java -jar로 실행 시 DB 접속 실패 | .env를 수동으로 source 해야 함 (set -a; source .env; set +a) |
| DB 데이터 유실 우려 | docker compose down은 볼륨 유지, docker compose down -v는 볼륨 삭제 (주의) |
| Nginx 502 Bad Gateway | 백엔드 서비스가 실행 중인지 확인 (systemctl status coopsket-backend) |
