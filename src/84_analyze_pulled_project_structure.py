"""Static project structure analyzer for pulled capstone_conv repository.

This script is intentionally not executed by the assistant.
It documents the checks used to generate the structure report.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def main() -> None:
    checks = {
        "root.front": exists("front"),
        "root.backend": exists("backend"),
        "root.ai": exists("Ai"),
        "frontend.package_json": exists("front/store-dashboard-frontend-main/package.json"),
        "frontend.src": exists("front/store-dashboard-frontend-main/src"),
        "frontend.vite": exists("front/store-dashboard-frontend-main/vite.config.js"),
        "backend.gradle": exists("backend/conv/build.gradle"),
        "backend.src_main": exists("backend/conv/src/main"),
        "backend.application_yml": exists("backend/conv/src/main/resources/application.yml"),
        "backend.env_example": exists("backend/conv/.env.example"),
        "ai.fastapi": exists("Ai/src/api_server.py"),
        "web_api_file": exists("front/store-dashboard-frontend-main/src/api/api.js"),
        "mobile_api_file": exists("App/app_fronted23/InventoryRequestApp/src/api/studentApi.ts"),
    }

    print("[pulled project structure checks]")
    for key, value in checks.items():
        print(f"{key}: {'OK' if value else 'MISSING'}")


if __name__ == "__main__":
    main()
