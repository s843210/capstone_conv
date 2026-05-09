"""Label-encoding helpers shared across training scripts."""

from __future__ import annotations

import pandas as pd


def label_encode_train_test(
    train_s: pd.Series,
    test_s: pd.Series,
) -> tuple[pd.Series, pd.Series, dict[str, int]]:
    """Build a mapping from *train_s* unique values and apply it to both
    *train_s* and *test_s*.  Unknown values in *test_s* become ``-1``.
    """
    train_vals = train_s.astype(str).fillna("")
    test_vals = test_s.astype(str).fillna("")
    classes = sorted(train_vals.unique().tolist())
    mapping = {v: i for i, v in enumerate(classes)}
    train_enc = train_vals.map(mapping).fillna(-1).astype(int)
    test_enc = test_vals.map(mapping).fillna(-1).astype(int)
    return train_enc, test_enc, mapping


def encode_with_mapping(
    values: pd.Series,
    mapping: dict[str, int],
) -> pd.Series:
    """Apply an existing label *mapping* to *values*.  Unknown values
    become ``-1``.
    """
    return values.astype(str).fillna("").map(mapping).fillna(-1).astype(int)
