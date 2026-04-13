from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import joblib

from .settings import settings


@dataclass
class ModelBundle:
    model: Any
    encoders: dict[str, Any]
    meta: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.meta.get("version", "v6"))

    @property
    def profile(self) -> str:
        return str(self.meta.get("profile", "small"))

    @property
    def feature_cols(self) -> list[str]:
        cols = self.meta.get("feature_cols")
        if cols is None:
            cols = self.meta.get("feature_columns", [])
        return [str(c) for c in cols]

    @property
    def log_transform_cols(self) -> set[str]:
        cols = self.meta.get("log_transform_cols", [])
        return {str(c) for c in cols}

    def _encode(self, encoder_key: str, raw_value: str) -> int:
        encoder = self.encoders.get(encoder_key)
        if encoder is None:
            return 0

        value = str(raw_value or "_unknown")
        classes = {str(c) for c in getattr(encoder, "classes_", [])}
        if value not in classes:
            if "_unknown" in classes:
                value = "_unknown"
            elif "기타" in classes:
                value = "기타"
            elif classes:
                value = next(iter(classes))
            else:
                return 0

        try:
            return int(encoder.transform([value])[0])
        except Exception:
            return 0

    def encode_category_l(self, value: str) -> int:
        return self._encode("category_l", value)

    def encode_category_m(self, value: str) -> int:
        return self._encode("category_m", value)


class ModelStore:
    def __init__(self) -> None:
        self.bundle: ModelBundle | None = None

    def load(self) -> ModelBundle:
        model_path = settings.model_path_obj
        enc_path = settings.encoder_path_obj
        meta_path = settings.meta_path_obj

        if not model_path.exists():
            raise FileNotFoundError(f"MODEL_PATH not found: {model_path}")
        if not enc_path.exists():
            raise FileNotFoundError(f"ENCODER_PATH not found: {enc_path}")
        if not meta_path.exists():
            raise FileNotFoundError(f"META_PATH not found: {meta_path}")

        model = joblib.load(model_path)
        enc_obj = joblib.load(enc_path)
        if isinstance(enc_obj, dict):
            encoders = enc_obj
        else:
            encoders = {"category_m": enc_obj}

        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)

        bundle = ModelBundle(model=model, encoders=encoders, meta=meta)
        if not bundle.feature_cols:
            raise ValueError("model_meta_v6.json must include feature_cols (or feature_columns)")

        self.bundle = bundle
        return bundle


model_store = ModelStore()
