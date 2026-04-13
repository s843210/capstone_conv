from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .settings import settings


@dataclass
class SpringPushResult:
    sent: bool
    status_code: int | None
    saved_count: int
    response_json: dict[str, Any] | None
    error: str | None


class SpringClient:
    def __init__(self) -> None:
        retry = Retry(
            total=settings.http_retry,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def send_predictions(self, payload: dict[str, Any]) -> SpringPushResult:
        url = settings.spring_base_url.rstrip("/") + settings.spring_ai_path
        try:
            response = self.session.post(url, json=payload, timeout=settings.http_timeout_sec)
            body: dict[str, Any] | None
            try:
                body = response.json()
            except Exception:
                body = None

            if response.status_code >= 400:
                return SpringPushResult(
                    sent=False,
                    status_code=response.status_code,
                    saved_count=0,
                    response_json=body,
                    error=f"HTTP {response.status_code}",
                )

            saved_count = 0
            if isinstance(body, dict):
                saved_count = int(body.get("savedCount", 0) or 0)

            return SpringPushResult(
                sent=True,
                status_code=response.status_code,
                saved_count=saved_count,
                response_json=body,
                error=None,
            )

        except Exception as exc:
            return SpringPushResult(
                sent=False,
                status_code=None,
                saved_count=0,
                response_json=None,
                error=str(exc),
            )
