# 백엔드 JWT + Google OAuth 흐름 요약

## 1. 로그인 방식

관리자는 백엔드 계정으로 로그인하고, 학생은 앱에서 Google OAuth로 로그인한다.

- 관리자: `POST /api/auth/admin/login`
- 학생: `POST /api/auth/google`

## 2. 학생 Google 로그인 흐름

1. 앱에서 Google 로그인 실행
2. Google이 `idToken` 발급
3. 앱이 백엔드로 `idToken` 전송

```http
POST /api/auth/google
```

```json
{
  "idToken": "Google ID Token"
}
```

4. 백엔드는 Google ID Token을 검증
5. 기존 학생이면 사용자 정보 업데이트
6. 신규 학생이면 `app_user` 테이블에 생성
7. 백엔드가 JWT 발급
8. 앱은 JWT를 저장하고 이후 API 요청에 사용

## 3. JWT 사용 방식

로그인 성공 시 백엔드는 아래 형태로 응답한다.

```json
{
  "accessToken": "JWT_TOKEN",
  "tokenType": "Bearer",
  "user": {
    "role": "STUDENT",
    "provider": "GOOGLE"
  }
}
```

이후 앱/프론트는 API 요청마다 헤더에 JWT를 붙인다.

```http
Authorization: Bearer JWT_TOKEN
```

## 4. 권한 분리

백엔드에서 JWT를 확인해서 사용자 역할을 구분한다.

- `ADMIN`: 관리자 대시보드 API 접근 가능
- `STUDENT`: 학생 앱 API 접근 가능

예시:

- `/api/admin/**`: 관리자만
- `/api/dashboard`: 관리자만
- `/api/inventory/**`: 관리자만
- `/api/student/**`: 학생 또는 관리자

## 5. 운영 서버에서 필요한 환경변수

EC2 백엔드 `.env`에 아래 값이 필요하다.

```env
JWT_SECRET=운영용_랜덤_문자열
JWT_ISSUER=campus-store
JWT_EXPIRATION_MINUTES=120

GOOGLE_CLIENT_IDS=웹클라이언트ID,안드로이드클라이언트ID
```

`GOOGLE_CLIENT_IDS`가 없으면 Google 로그인 검증이 실패한다.

## 6. 전체 흐름

```text
학생 앱
-> Google 로그인
-> Google ID Token 발급
-> 백엔드 /api/auth/google 전송
-> 백엔드가 Google 토큰 검증
-> app_user 조회 또는 생성
-> JWT 발급
-> 앱이 JWT 저장
-> 이후 API 요청에 Bearer Token 사용
```
