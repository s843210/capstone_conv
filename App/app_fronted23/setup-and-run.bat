@echo off
setlocal

set APP_NAME=InventoryRequestApp

where npx >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npx not found. Install Node.js LTS first.
  exit /b 1
)

if exist %APP_NAME% (
  echo [INFO] %APP_NAME% folder already exists. Skipping Expo init.
) else (
  call npx create-expo-app@latest %APP_NAME% --template blank-typescript --yes
  if errorlevel 1 (
    echo [ERROR] Expo project init failed.
    exit /b 1
  )
)

copy /Y App.tsx %APP_NAME%\App.tsx >nul
if errorlevel 1 (
  echo [ERROR] Failed to copy App.tsx
  exit /b 1
)

cd %APP_NAME%
call npm install @react-navigation/native @react-navigation/native-stack
if errorlevel 1 (
  echo [ERROR] Navigation package install failed.
  exit /b 1
)

call npx expo install react-native-screens react-native-safe-area-context
if errorlevel 1 (
  echo [ERROR] Dependency install failed.
  exit /b 1
)

echo.
echo [DONE] Project is ready.
echo Run these commands:
echo   cd %APP_NAME%
echo   npx expo start
echo   npx expo start --android

endlocal
