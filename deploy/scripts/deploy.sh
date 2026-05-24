#!/bin/bash
# ============================================
# Coopsket 배포 자동화 스크립트
# 사용법: bash deploy/scripts/deploy.sh
# EC2 서버에서 실행 (초기 배포 또는 업데이트 시)
# ============================================

set -e

PROJECT_DIR="/home/ubuntu/capston_conv"
BACKEND_DIR="$PROJECT_DIR/backend/conv"
FRONTEND_DIR="$PROJECT_DIR/front/store-dashboard-frontend-main"
AI_DIR="$PROJECT_DIR/Ai"
ENV_FILE="$BACKEND_DIR/.env"

echo "=========================================="
echo "  Coopsket 배포 시작"
echo "=========================================="

# 1. 최신 코드 가져오기
echo "[1/7] 최신 코드 pull..."
cd "$PROJECT_DIR"
git pull
git lfs pull

# 2. 환경변수 로드
echo "[2/7] 환경변수 로드..."
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE 파일이 없습니다."
    echo "  cp deploy/.env.example backend/conv/.env 후 실제 값을 입력하세요."
    exit 1
fi
set -a; source "$ENV_FILE"; set +a

# 3. PostgreSQL 실행 확인
echo "[3/7] PostgreSQL 컨테이너 확인..."
cd "$BACKEND_DIR"
docker compose up -d db
sleep 3
docker ps | grep campus-store-db || { echo "ERROR: DB 컨테이너 시작 실패"; exit 1; }

# 4. Spring Boot 빌드 + 재시작
echo "[4/7] Spring Boot 빌드..."
cd "$BACKEND_DIR"
chmod +x ./gradlew
./gradlew clean build -x test
sudo systemctl restart coopsket-backend
sleep 5
sudo systemctl is-active coopsket-backend || { echo "ERROR: 백엔드 시작 실패"; exit 1; }

# 5. AI FastAPI 의존성 + 재시작
echo "[5/7] AI FastAPI 설정..."
cd "$AI_DIR"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate
sudo systemctl restart coopsket-ai
sleep 3
sudo systemctl is-active coopsket-ai || { echo "ERROR: AI 서비스 시작 실패"; exit 1; }

# 6. 프론트엔드 빌드 + Nginx 배치
echo "[6/7] 프론트엔드 빌드..."
cd "$FRONTEND_DIR"
npm ci
npm run build
sudo mkdir -p /var/www/coopsket
sudo rsync -a --delete dist/ /var/www/coopsket/

# 7. Nginx 설정 적용
echo "[7/7] Nginx 설정 적용..."
sudo cp "$PROJECT_DIR/deploy/nginx/coopsket" /etc/nginx/sites-available/coopsket
sudo ln -sf /etc/nginx/sites-available/coopsket /etc/nginx/sites-enabled/coopsket
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "=========================================="
echo "  배포 완료!"
echo "=========================================="
echo ""
echo "확인 사항:"
echo "  - 웹: http://$(hostname -I | awk '{print $1}')"
echo "  - API: curl http://localhost/api/auth/me (401이면 정상)"
echo "  - DB:  docker ps | grep campus-store-db"
echo "  - 백엔드: sudo systemctl status coopsket-backend"
echo "  - AI:  sudo systemctl status coopsket-ai"
