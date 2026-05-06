#!/usr/bin/env bash
set -euo pipefail

APP_NAME="InventoryRequestApp"

if ! command -v npx >/dev/null 2>&1; then
  echo "[ERROR] npx not found. Install Node.js LTS first."
  exit 1
fi

if [ -d "$APP_NAME" ]; then
  echo "[INFO] $APP_NAME folder already exists. Skipping Expo init."
else
  npx create-expo-app@latest "$APP_NAME" --template blank-typescript --yes
fi

cp -f App.tsx "$APP_NAME/App.tsx"

cd "$APP_NAME"
npm install @react-navigation/native @react-navigation/native-stack
npx expo install react-native-screens react-native-safe-area-context

echo
echo "[DONE] Project is ready."
echo "Run these commands:"
echo "  cd $APP_NAME"
echo "  npx expo start"
echo "  npx expo start --ios"
echo "  npx expo start --android"
