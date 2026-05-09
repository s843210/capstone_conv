from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PRODUCT_ROOT = BASE_DIR / "data" / "raw" / "product" / "product_master" / "csv_상품분류기준표"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "product_master.csv"
LOG_PATH = BASE_DIR / "outputs" / "reports" / "product_master_merge_log.txt"
TARGET_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def normalize_key(text: object) -> str:
    s = str(text)
    s = s.replace("\n", "").replace("\r", "")
    s = re.sub(r"\s+", "", s)
    return s.strip().lower()


def find_header_row(df_no_header: pd.DataFrame, max_scan_rows: int = 30) -> Optional[int]:
    rows_to_scan = min(len(df_no_header), max_scan_rows)
    for i in range(rows_to_scan):
        vals = [normalize_key(v) for v in df_no_header.iloc[i].tolist()]
        has_name = any(v in {"상품명", "품명", "상품"} for v in vals)
        has_plu = any("plu" in v and ("코드" in v or "code" in v or v == "plu") for v in vals)
        if has_name and has_plu:
            return i
    return None


def read_one_file(file_path: Path) -> pd.DataFrame:
    ext = file_path.suffix.lower()

    if ext in {".xlsx", ".xls"}:
        preview = pd.read_excel(file_path, header=None, nrows=40)
        header_row = find_header_row(preview)
        if header_row is None:
            raise ValueError("Could not detect header row (상품명/PLU코드).")
        df = pd.read_excel(file_path, header=header_row)
        return df

    if ext == ".csv":
        try:
            preview = pd.read_csv(file_path, header=None, nrows=40, encoding="utf-8")
            header_row = find_header_row(preview)
            if header_row is None:
                raise ValueError("Could not detect header row (상품명/PLU코드).")
            return pd.read_csv(file_path, header=header_row, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            preview = pd.read_csv(file_path, header=None, nrows=40, encoding="cp949")
            header_row = find_header_row(preview)
            if header_row is None:
                raise ValueError("Could not detect header row (상품명/PLU코드).")
            return pd.read_csv(file_path, header=header_row, encoding="cp949", low_memory=False)

    raise ValueError(f"Unsupported extension: {ext}")


def get_column_mapping(df: pd.DataFrame) -> dict[str, str]:
    norm_to_col = {normalize_key(c): c for c in df.columns}

    product_col = None
    plu_col = None
    category_col = None

    for k, v in norm_to_col.items():
        if product_col is None and k in {"상품명", "품명", "상품"}:
            product_col = v
        if plu_col is None and ("plu" in k and ("코드" in k or "code" in k or k == "plu")):
            plu_col = v
        if category_col is None and ("분류" in k or "카테고리" in k):
            category_col = v

    if product_col is None:
        for k, v in norm_to_col.items():
            if "상품명" in k:
                product_col = v
                break

    if plu_col is None:
        for k, v in norm_to_col.items():
            if "plu" in k:
                plu_col = v
                break

    mapping: dict[str, str] = {}
    if product_col:
        mapping[product_col] = "product_name"
    if plu_col:
        mapping[plu_col] = "plu_code"
    if category_col:
        mapping[category_col] = "product_category"
    return mapping


def clean_category_from_filename(file_path: Path) -> str:
    return file_path.stem.strip()


def process_file(file_path: Path) -> pd.DataFrame:
    df = read_one_file(file_path)
    col_map = get_column_mapping(df)
    df = df.rename(columns=col_map)

    if "product_name" not in df.columns:
        raise KeyError("product_name column not found.")
    if "plu_code" not in df.columns:
        raise KeyError("plu_code column not found.")

    if "product_category" not in df.columns:
        df["product_category"] = clean_category_from_filename(file_path)
    else:
        df["product_category"] = df["product_category"].fillna("").astype(str).str.strip()
        fallback = clean_category_from_filename(file_path)
        df.loc[df["product_category"] == "", "product_category"] = fallback

    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["plu_code"] = df["plu_code"].astype(str).str.strip()
    df = df[(df["product_name"] != "") & (df["product_name"].str.lower() != "nan")]
    df = df[(df["plu_code"] != "") & (df["plu_code"].str.lower() != "nan")]

    # remove obvious header/summary rows kept in body
    df = df[~df["product_name"].str.contains(r"^(?:상품명|합계|총계)$", regex=True, na=False)]
    df = df[~df["plu_code"].str.contains(r"^(?:plu|plu코드|코드)$", regex=True, na=False)]

    df["source_file"] = file_path.relative_to(BASE_DIR).as_posix()
    return df[["product_name", "plu_code", "product_category", "source_file"]].copy()


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(
        [p for p in PRODUCT_ROOT.rglob("*") if p.is_file() and p.suffix.lower() in TARGET_EXTENSIONS]
    )

    success = 0
    failed: list[tuple[str, str]] = []
    frames: list[pd.DataFrame] = []
    before_dedup = 0

    for fp in files:
        try:
            out = process_file(fp)
            frames.append(out)
            success += 1
            before_dedup += len(out)
        except Exception as exc:
            failed.append((fp.relative_to(BASE_DIR).as_posix(), str(exc)))

    if frames:
        merged = pd.concat(frames, ignore_index=True)
    else:
        merged = pd.DataFrame(columns=["product_name", "plu_code", "product_category", "source_file"])

    merged = merged.drop_duplicates(subset=["product_name", "plu_code"], keep="first").reset_index(drop=True)
    merged.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    log_lines: list[str] = []
    log_lines.append("Product Master Merge Log")
    log_lines.append(f"target_directory: {PRODUCT_ROOT.as_posix()}")
    log_lines.append(f"total_target_files: {len(files)}")
    log_lines.append(f"success_files: {success}")
    log_lines.append(f"failed_files: {len(failed)}")
    log_lines.append(f"rows_before_dedup: {before_dedup}")
    log_lines.append(f"rows_after_dedup: {len(merged)}")
    log_lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    log_lines.append("")
    log_lines.append("[Failed Files]")
    if failed:
        for rel, reason in failed:
            log_lines.append(f"- file: {rel}")
            log_lines.append(f"  reason: {reason}")
    else:
        log_lines.append("None")

    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")

    print(f"Total target files: {len(files)}")
    print(f"Success files: {success}")
    print(f"Failed files: {len(failed)}")
    print(f"Rows before dedup: {before_dedup}")
    print(f"Rows after dedup: {len(merged)}")
    print(f"Saved CSV: {OUTPUT_CSV}")
    print(f"Saved log: {LOG_PATH}")


if __name__ == "__main__":
    main()
