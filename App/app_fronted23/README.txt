# 전달용 Expo 앱 패키지

이 폴더는 **코드 전달용**입니다.
받는 사람이 이 폴더를 압축 해제한 뒤 운영체제에 맞는 스크립트(`setup-and-run.bat` 또는 `setup-and-run.sh`)를 실행하면 Expo 기본 프로젝트를 만들고, 현재 앱 코드(`App.tsx`)를 자동 반영합니다.

## 포함 파일
- `App.tsx`: 앱 화면/흐름 코드
- `setup-and-run.bat`: Windows용 Expo 프로젝트 자동 생성/의존성 설치 스크립트
- `setup-and-run.sh`: macOS/Linux용 Expo 프로젝트 자동 생성/의존성 설치 스크립트
- `package.sample.json`: 참고용 의존성 목록

## 받는 사람 실행 방법(Windows)
1. Node.js LTS 설치
2. (선택) Expo Go 앱 설치(실기기 테스트 시)
3. 이 폴더에서 `setup-and-run.bat` 더블클릭 또는 터미널 실행
4. 완료 후 아래 실행
   - `cd InventoryRequestApp`
   - `npx expo start`
5. Android 에뮬레이터 실행 시
   - `npx expo start --android`

## 받는 사람 실행 방법(macOS/Linux)
1. Node.js LTS 설치
2. 이 폴더에서 실행 권한 부여
   - `chmod +x setup-and-run.sh`
3. 스크립트 실행
   - `./setup-and-run.sh`
4. 완료 후 아래 실행
   - `cd InventoryRequestApp`
   - `npx expo start`
5. 시뮬레이터/에뮬레이터 실행
   - iOS: `npx expo start --ios` (macOS + Xcode 필요)
   - Android: `npx expo start --android` (Android Studio 필요)

## 중요
- `npm install`은 `C:\Users\...\app` 루트에서 하면 안 됩니다.
- 반드시 Expo 프로젝트 폴더(자동 생성되는 `InventoryRequestApp`) 안에서 실행해야 합니다.
