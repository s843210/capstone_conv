# Capstone Project

이 레포지토리는 캡스톤 프로젝트를 위한 저장소입니다. `front`, `Ai`, `backend` 세 개의 주요 디렉토리로 구성되어 있습니다.

## 📁 폴더 구조

- `front/`: 프론트엔드 코드 공간 (React, Vue 등)
- `Ai/`: AI 및 모델 관련 코드 공간 (Python, Jupyter 빌드 등)
- `backend/`: 백엔드 서버 및 API 통신 코드 공간 (Node.js, Spring Boot, Django 등)

---

## 🌿 Git 협업 워크플로우 (Branch Strategy)

우리 팀은 원활한 협업과 충돌 방지를 위해 **Git Flow (또는 GitHub Flow)** 기반의 협업 전략을 따릅니다. 

### 브랜치 종류
1. **`main`**: 실제 서비스가 배포되는 가장 안정적인 코드가 있는 브랜치
2. **`develop`**: 배포 전 기능들이 모여서 테스트되는 중심 개발 브랜치. 다음 배포를 위해 기능들이 모이는 곳입니다.
3. **`feature/[기능이름]`**: 각 팀원이 개별 기능을 개발할 때 사용하는 브랜치입니다. (예: `feature/login`, `feature/db-setup`)

---

### 💻 작업 순서 (Workflow)

**1. 새로운 기능을 개발하기 위해 브랜치 생성하기**
개발을 시작할 때는 항상 `develop` 브랜치를 기준으로 최신 코드를 받고, 내 기능용 새 브랜치를 만듭니다.

```bash
git checkout develop           # 기준 브랜치(develop)로 이동
git pull                       # 다른 팀원이 작업한 최신 변경사항을 내 로컬로 가져오기
git checkout -b feature/login  # 'feature/login' 이라는 새 브랜치를 생성하고 바로 이동
```

**2. 코드 작성 및 저장하기**
내 브랜치에서 코드를 열심히 작성한 다음, 작업 내역을 커밋(저장)합니다.

```bash
git add .
git commit -m "feat: 카카오 로그인 기능 추가"
```

**3. 작성한 코드를 GitHub에 올리기 (Push)**
```bash
git push origin feature/login  # 내 브랜치를 원격(GitHub) 저장소로 올리기
```

**4. Pull Request (PR) 및 코드 병합 (Merge)**
- GitHub 레포지토리 페이지에 들어가면 `Compare & pull request` 초록색 버튼이 뜹니다.
- **`feature/login`** 브랜치를 **`develop`** 브랜치로 병합하겠다는 **Pull Request(PR)**를 생성합니다.
- 팀원들이 코드를 리뷰하고 승인(Approve)하면, **Merge pull request** 버튼을 눌러 `develop` 브랜치에 합칩니다.

**5. 내 로컬 및 브랜치 정리 (선택사항)**
```bash
git checkout develop      # 다시 중심 브랜치로 돌아가서
git pull                  # 방금 합쳐진 새로운 코드를 내려받습니다
git branch -d feature/login # 작업이 완벽히 끝난 브랜치는 삭제해도 무방합니다
```

> **🔥 주의사항**
> 절대로 `main` 이나 `develop` 브랜치에 직접 코드를 Push 하거나 커밋하지 마세요!
> 항상 새로운 `feature/xxx` 브랜치에서 작업 후 PR을 통해 병합(Merge)하는 문화를 지향합니다.
