"""Ingest — merge raw Excel sales files and product master into processed CSVs.

Consolidates logic from legacy scripts 04, 08, 10, 13.
"""

from __future__ import annotations

import re
from datetime import date as _date
from pathlib import Path
from typing import Optional

import pandas as pd

from ..config import BASE_DIR, Paths, Preprocessing
from ..utils.io import safe_save_csv, ensure_dir
from ..utils.date_parse import extract_date_from_path
from ..utils.text_norm import extract_category_from_filename, normalize_column_key
from ..utils.report import write_report


# ===================================================================
# Sales file merging  (legacy 08_merge_all_sales_files_v2)
# ===================================================================

def _find_real_header_row(
    file_path: Path,
    keyword: str = Preprocessing.HEADER_KEYWORD,
    max_scan: int = 50,
) -> Optional[int]:
    preview = pd.read_excel(file_path, header=None, nrows=max_scan)
    for i in range(len(preview)):
        row = preview.iloc[i].astype(str).str.strip()
        if (row == keyword).any():
            return i
    return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    norm_map: dict[str, str] = {}
    for col in df.columns:
        key = re.sub(r"\s+", "", str(col))
        norm_map[key] = col

    rename: dict[str, str] = {}
    if "카테고리/상품" in norm_map:
        rename[norm_map["카테고리/상품"]] = "product_name"
    if "매입합계" in norm_map:
        rename[norm_map["매입합계"]] = "purchase_qty"
    if "매출합계" in norm_map:
        rename[norm_map["매출합계"]] = "sales_qty"
    return df.rename(columns=rename)


def _clean_sales_df(df: pd.DataFrame) -> pd.DataFrame:
    required = ["product_name", "purchase_qty", "sales_qty"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns after normalisation: {missing}")

    work = df[required].copy()
    work["product_name"] = work["product_name"].astype(str).str.strip()
    work = work[work["product_name"].notna()]
    work = work[work["product_name"] != ""]
    work = work[work["product_name"].str.lower() != "nan"]
    work = work[
        ~work["product_name"].str.contains(
            Preprocessing.SUMMARY_PATTERN, regex=True, na=False
        )
    ]
    work["purchase_qty"] = pd.to_numeric(work["purchase_qty"], errors="coerce")
    work["sales_qty"] = pd.to_numeric(work["sales_qty"], errors="coerce")
    work = work.dropna(how="all", subset=["purchase_qty", "sales_qty"])
    return work


def _infer_latest_date_from_sheet(raw_df: pd.DataFrame, fallback_date: str) -> str:
    """Infer latest available day from sheet headers like ``05-09``.

    Monthly raw files are often named like ``2605...xlsx`` and would otherwise
    map to ``YYYY-MM-01`` by filename parsing. This helper looks at the first
    data row (just below the header row), detects day headers, and upgrades the
    date to the latest day that has at least one numeric value in the column.
    """
    try:
        base = pd.to_datetime(fallback_date, errors="coerce")
    except Exception:
        base = pd.NaT
    if pd.isna(base):
        return fallback_date

    if raw_df.empty:
        return fallback_date

    first_row = raw_df.iloc[0]
    latest_day: int | None = None

    for col in raw_df.columns:
        token = str(first_row.get(col, "")).strip()
        m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", token)
        if not m:
            continue

        month = int(m.group(1))
        day = int(m.group(2))
        if month != int(base.month):
            continue

        # Exclude header-like columns that do not have numeric body values.
        col_num = pd.to_numeric(raw_df[col], errors="coerce")
        if len(col_num) <= 1 or not col_num.iloc[1:].notna().any():
            continue

        latest_day = day if latest_day is None else max(latest_day, day)

    if latest_day is None:
        return fallback_date

    try:
        resolved = _date(int(base.year), int(base.month), int(latest_day))
    except ValueError:
        return fallback_date
    return resolved.strftime("%Y-%m-%d")


def _process_one_sales_file(file_path: Path) -> pd.DataFrame:
    header_row = _find_real_header_row(file_path)
    if header_row is None:
        raise ValueError(f'Header row with "{Preprocessing.HEADER_KEYWORD}" not found.')

    raw = pd.read_excel(file_path, header=header_row)
    cleaned = _clean_sales_df(_normalize_columns(raw))

    date_val = extract_date_from_path(file_path)
    date_val = _infer_latest_date_from_sheet(raw, date_val)
    cat_val = extract_category_from_filename(file_path.stem)
    src = file_path.relative_to(BASE_DIR).as_posix()

    cleaned.insert(0, "category", cat_val)
    cleaned.insert(0, "date", date_val)
    cleaned["source_file"] = src
    return cleaned[
        ["date", "category", "product_name", "purchase_qty", "sales_qty", "source_file"]
    ].copy()


def merge_sales_files(
    sales_dir: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Scan *sales_dir* for Excel files and merge them into a single CSV."""
    sales_dir = sales_dir or Paths.SALES_DIR
    output_csv = output_csv or Paths.DAILY_SALES_RAW
    report_path = Paths.REPORTS_DIR / "merge_sales_log.txt"

    all_files = sorted(
        p for p in sales_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in Preprocessing.EXCEL_EXTENSIONS
    )

    frames: list[pd.DataFrame] = []
    failed: list[tuple[str, str]] = []
    for fp in all_files:
        try:
            frames.append(_process_one_sales_file(fp))
        except Exception as exc:
            failed.append((fp.relative_to(BASE_DIR).as_posix(), str(exc)))

    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["date", "category", "product_name", "purchase_qty", "sales_qty", "source_file"]
    )

    safe_save_csv(merged, output_csv)

    lines = [
        "Merge Sales Files Log",
        f"target_directory: {sales_dir.as_posix()}",
        f"total_files: {len(all_files)}",
        f"success: {len(frames)}",
        f"failed: {len(failed)}",
        f"rows: {len(merged)}",
        f"output: {output_csv.as_posix()}",
    ]
    if failed:
        lines.append("\n[Failed Files]")
        for path_text, reason in failed:
            lines += [f"- {path_text}", f"  reason: {reason}"]

    write_report(report_path, lines)
    print(f"Sales merge: {len(frames)} files → {len(merged)} rows → {output_csv.name}")
    return merged


# ===================================================================
# Product master merging  (legacy 10_merge_product_master)
# ===================================================================

def _find_product_header_row(
    df_no_header: pd.DataFrame,
    max_scan: int = 30,
) -> Optional[int]:
    for i in range(min(len(df_no_header), max_scan)):
        vals = [normalize_column_key(v) for v in df_no_header.iloc[i].tolist()]
        has_name = any(v in {"상품명", "품명", "상품"} for v in vals)
        has_plu = any("plu" in v for v in vals)
        if has_name and has_plu:
            return i
    return None


def _read_product_file(file_path: Path) -> pd.DataFrame:
    ext = file_path.suffix.lower()
    if ext in {".xlsx", ".xls"}:
        preview = pd.read_excel(file_path, header=None, nrows=40)
        hr = _find_product_header_row(preview)
        if hr is None:
            raise ValueError("Header row not found (상품명/PLU).")
        return pd.read_excel(file_path, header=hr)
    if ext == ".csv":
        try:
            preview = pd.read_csv(file_path, header=None, nrows=40, encoding="utf-8")
        except UnicodeDecodeError:
            preview = pd.read_csv(file_path, header=None, nrows=40, encoding="cp949")
        hr = _find_product_header_row(preview)
        if hr is None:
            raise ValueError("Header row not found (상품명/PLU).")
        try:
            return pd.read_csv(file_path, header=hr, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            return pd.read_csv(file_path, header=hr, encoding="cp949", low_memory=False)
    raise ValueError(f"Unsupported extension: {ext}")


def _get_product_column_mapping(df: pd.DataFrame) -> dict[str, str]:
    norm = {normalize_column_key(c): c for c in df.columns}
    mapping: dict[str, str] = {}
    for k, v in norm.items():
        if "상품명" in k or k in {"품명", "상품"}:
            mapping.setdefault(v, "product_name")
        if "plu" in k:
            mapping.setdefault(v, "plu_code")
        if "분류" in k or "카테고리" in k:
            mapping.setdefault(v, "product_category")
    # Reverse so rename dict is original→target
    return {orig: target for orig, target in mapping.items()}


def merge_product_master(
    product_dir: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Merge product master files into one deduplicated CSV."""
    product_dir = product_dir or Paths.PRODUCT_MASTER_DIR
    output_csv = output_csv or Paths.PRODUCT_MASTER
    report_path = Paths.REPORTS_DIR / "product_master_merge_log.txt"

    files = sorted(
        p for p in product_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".xlsx", ".xls", ".csv"}
    )

    frames: list[pd.DataFrame] = []
    failed: list[tuple[str, str]] = []
    for fp in files:
        try:
            df = _read_product_file(fp)
            col_map = _get_product_column_mapping(df)
            df = df.rename(columns=col_map)
            if "product_name" not in df.columns or "plu_code" not in df.columns:
                raise KeyError("product_name / plu_code not found")
            if "product_category" not in df.columns:
                df["product_category"] = fp.stem.strip()
            df["product_name"] = df["product_name"].astype(str).str.strip()
            df["plu_code"] = df["plu_code"].astype(str).str.strip()
            df = df[(df["product_name"] != "") & (df["product_name"].str.lower() != "nan")]
            df = df[(df["plu_code"] != "") & (df["plu_code"].str.lower() != "nan")]
            df["source_file"] = fp.relative_to(BASE_DIR).as_posix()
            frames.append(df[["product_name", "plu_code", "product_category", "source_file"]].copy())
        except Exception as exc:
            failed.append((fp.relative_to(BASE_DIR).as_posix(), str(exc)))

    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["product_name", "plu_code", "product_category", "source_file"]
    )
    merged = merged.drop_duplicates(subset=["product_name", "plu_code"], keep="first").reset_index(drop=True)
    safe_save_csv(merged, output_csv)

    lines = [
        "Product Master Merge Log",
        f"total_files: {len(files)}, success: {len(frames)}, failed: {len(failed)}",
        f"rows: {len(merged)}",
        f"output: {output_csv.as_posix()}",
    ]
    write_report(report_path, lines)
    print(f"Product master: {len(frames)} files → {len(merged)} rows → {output_csv.name}")
    return merged
