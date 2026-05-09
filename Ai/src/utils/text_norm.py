"""Text normalisation helpers — product name cleaning, column normalisation."""

from __future__ import annotations

import re


def normalize_column_key(text: str) -> str:
    """Strip all whitespace from a column name for fuzzy matching."""
    return re.sub(r"\s+", "", str(text)).strip().lower()


def normalize_product_name(name: str) -> str:
    """Normalise a product name for matching: lowercase, strip spaces, remove
    brackets content, etc.
    """
    s = str(name).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def extract_category_from_filename(file_path_stem: str) -> str:
    """Strip leading 4-digit prefix (YYMM or MMDD) from filename stem to
    extract the category name.

    Example: ``2410가공식품`` → ``가공식품``
    """
    category = re.sub(r"^\d{4}", "", file_path_stem).strip()
    if not category:
        raise ValueError(f"Could not extract category from: {file_path_stem}")
    return category
