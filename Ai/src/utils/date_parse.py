"""Date parsing helpers — YYMMDD extraction from file paths."""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import pandas as pd


def extract_date_from_path(file_path: Path) -> str:
    """Extract a date string (``YYYY-MM-DD``) from *file_path*.

    Strategy:
      1. Look for a 6-digit ``YYMMDD`` token in any path component
         (e.g. ``240301`` → ``2024-03-01``).
      2. If the filename starts with 4 digits ``YYMM``, treat it as
         the 1st of that month.
    """
    # 1) YYMMDD folder token
    for part in file_path.parts:
        if re.fullmatch(r"\d{6}", part):
            yy, mm, dd = int(part[:2]), int(part[2:4]), int(part[4:6])
            return f"{2000 + yy:04d}-{mm:02d}-{dd:02d}"

    # 2) YYMM prefix in filename
    m = re.match(r"^(\d{2})(\d{2})", file_path.stem)
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        return f"{2000 + yy:04d}-{mm:02d}-01"

    raise ValueError(f"Could not extract date from: {file_path}")


def parse_date_series(series: pd.Series) -> pd.Series:
    """Parse a date series that may contain ``YYMMDD`` integers or normal
    date strings.
    """
    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, format="%y%m%d", errors="coerce")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        fallback = pd.to_datetime(s, errors="coerce")
    return parsed.fillna(fallback)
