from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "conv-fastapi-v6"
    tz: str = "Asia/Seoul"

    database_url: str = Field(
        default=f"sqlite:///{BASE_DIR / 'fastapi_v6.sqlite3'}",
        alias="DATABASE_URL",
    )

    spring_base_url: str = Field(default="http://127.0.0.1:8080", alias="SPRING_BASE_URL")
    spring_ai_path: str = Field(default="/api/ai/predictions", alias="SPRING_AI_PATH")
    http_timeout_sec: int = Field(default=10, alias="HTTP_TIMEOUT_SEC")
    http_retry: int = Field(default=3, alias="HTTP_RETRY")

    model_path: str = Field(
        default=str(BASE_DIR / "saved_models" / "rf_sales_forecast_v6.pkl"),
        alias="MODEL_PATH",
    )
    encoder_path: str = Field(
        default=str(BASE_DIR / "saved_models" / "label_encoders_v6.pkl"),
        alias="ENCODER_PATH",
    )
    meta_path: str = Field(
        default=str(BASE_DIR / "saved_models" / "model_meta_v6.json"),
        alias="META_PATH",
    )

    run_artifact_dir: str = Field(default=str(BASE_DIR / "runs"), alias="RUN_ARTIFACT_DIR")
    keep_runs: int = Field(default=30, alias="KEEP_RUNS")

    enable_internal_scheduler: bool = Field(default=False, alias="ENABLE_INTERNAL_SCHEDULER")
    schedule_hour: int = Field(default=17, alias="SCHEDULE_HOUR")
    schedule_minute: int = Field(default=50, alias="SCHEDULE_MINUTE")

    @property
    def model_path_obj(self) -> Path:
        return Path(self.model_path)

    @property
    def encoder_path_obj(self) -> Path:
        return Path(self.encoder_path)

    @property
    def meta_path_obj(self) -> Path:
        return Path(self.meta_path)

    @property
    def run_artifact_dir_obj(self) -> Path:
        return Path(self.run_artifact_dir)


settings = Settings()
