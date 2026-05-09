"""File I/O helpers — csv/xlsx reading, safe saving, directory creation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def ensure_dir(path: Path) -> Path:
    """Create parent directories for *path* if they do not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def safe_read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV with UTF-8 first, falling back to cp949."""
    try:
        return pd.read_csv(path, low_memory=False, **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", low_memory=False, **kwargs)


def safe_read_excel(
    path: Path,
    header: int | None = 0,
    **kwargs: Any,
) -> pd.DataFrame:
    """Read an Excel file with the given header row index."""
    return pd.read_excel(path, header=header, **kwargs)


def safe_save_csv(df: pd.DataFrame, path: Path, **kwargs: Any) -> Path:
    """Save a DataFrame to CSV with UTF-8-SIG encoding."""
    ensure_dir(path)
    df.to_csv(path, index=False, encoding="utf-8-sig", **kwargs)
    return path
