from __future__ import annotations

import json
from pathlib import Path

from .settings import settings


def _ensure_root() -> Path:
    root = settings.run_artifact_dir_obj
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_run_dir(run_id: str) -> Path:
    root = _ensure_root()
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_json(run_dir: Path, name: str, payload: dict) -> None:
    with (run_dir / name).open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_text(run_dir: Path, name: str, content: str) -> None:
    with (run_dir / name).open("w", encoding="utf-8") as f:
        f.write(content)


def cleanup_old_runs() -> None:
    root = _ensure_root()
    dirs = [p for p in root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for stale in dirs[settings.keep_runs :]:
        for child in stale.rglob("*"):
            if child.is_file():
                child.unlink(missing_ok=True)
        for child in sorted(stale.rglob("*"), reverse=True):
            if child.is_dir():
                child.rmdir()
        stale.rmdir()
