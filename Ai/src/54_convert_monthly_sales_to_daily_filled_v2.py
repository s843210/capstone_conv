from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SALES_MONTHLY_DIR = BASE_DIR / "data" / "raw" / "sales_monthly"
PRODUCT_MASTER_REP_PATH = BASE_DIR / "data" / "processed" / "product_master_representative.csv"
V1_REPORT_PATH = BASE_DIR / "outputs" / "reports" / "monthly_sales_converter_report.txt"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "monthly_sales_daily_filled_v2.csv"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "monthly_sales_converter_v2_report.txt"
TARGET_EXT = {".xlsx", ".xls", ".csv"}

PRODUCT_COL_KEYWORDS = ["상품", "품목", "제품", "item", "product", "sku", "카테고리/상품", "품명", "category"]
PURCHASE_COL_KEYWORDS = ["매입", "입고", "발주", "purchase", "buy"]
SUMMARY_ROW_KEYWORDS = ["합계", "총계", "소계", "카테고리", "분류"]


@dataclass
class FileResult:
    file_path: Path
    success: bool
    message: str


def normalize_text(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_key(value: object) -> str:
    text = normalize_text(value).lower()
    for ch in [" ", "_", "-", "/", "(", ")", "[", "]", ".", "\t", "\n", ":"]:
        text = text.replace(ch, "")
    return text


def normalize_product_name(value: object) -> str:
    return normalize_key(value)


def extract_year_month(file_path: Path) -> Optional[str]:
    for part in reversed(file_path.parts):
        m = re.fullmatch(r"(20\d{2})(0[1-9]|1[0-2])", part)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
    m2 = re.match(r"^(\d{2})(0[1-9]|1[0-2])", file_path.stem)
    if m2:
        return f"20{m2.group(1)}-{m2.group(2)}"
    return None


def is_purchase_text(value: object) -> bool:
    k = normalize_key(value)
    return any(normalize_key(x) in k for x in PURCHASE_COL_KEYWORDS)


def is_summary_product(product_name: str) -> bool:
    k = normalize_key(product_name)
    return any(normalize_key(x) in k for x in SUMMARY_ROW_KEYWORDS)


def parse_day_token(value: object, ym: str) -> Optional[pd.Timestamp]:
    y = int(ym[:4])
    m = int(ym[5:7])
    last_day = calendar.monthrange(y, m)[1]

    if isinstance(value, pd.Timestamp):
        ts = pd.Timestamp(value)
        if ts.year == y and ts.month == m:
            return ts.normalize()
        return None

    text = normalize_text(value)
    if text == "" or text.lower() == "nan":
        return None

    m1 = re.fullmatch(r"(0?[1-9]|[12]\d|3[01])", text)
    if m1:
        day = int(m1.group(1))
        if day <= last_day:
            return pd.Timestamp(year=y, month=m, day=day)
        return None

    m2 = re.fullmatch(r"(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])", text)
    if m2:
        mm = int(m2.group(1))
        dd = int(m2.group(2))
        if mm == m and dd <= last_day:
            return pd.Timestamp(year=y, month=m, day=dd)
        return None

    m3 = re.fullmatch(r"\d{4}[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])", text)
    if m3:
        ts = pd.to_datetime(text, errors="coerce")
        if pd.notna(ts) and ts.year == y and ts.month == m and ts.day <= last_day:
            return ts.normalize()
    return None


def detect_product_header_row(raw: pd.DataFrame, top_n: int = 30) -> Optional[int]:
    best_row = None
    best_score = -1
    for i in range(min(top_n, len(raw))):
        vals = raw.iloc[i].tolist()
        score = 0
        for v in vals:
            k = normalize_key(v)
            if any(normalize_key(x) in k for x in PRODUCT_COL_KEYWORDS):
                score += 3
            if is_purchase_text(v):
                score += 1
        if score > best_score:
            best_score = score
            best_row = i
    if best_score <= 0:
        return None
    return best_row


def detect_date_header_row(raw: pd.DataFrame, ym: str, top_n: int = 30) -> Optional[int]:
    best_row = None
    best_count = -1
    for i in range(min(top_n, len(raw))):
        vals = raw.iloc[i].tolist()
        cnt = sum(1 for v in vals if parse_day_token(v, ym) is not None)
        if cnt > best_count:
            best_count = cnt
            best_row = i
    if best_count < 3:
        return None
    return best_row


def detect_product_col_idx(raw: pd.DataFrame, header_row: Optional[int]) -> int:
    if header_row is not None:
        vals = raw.iloc[header_row].tolist()
        for j, v in enumerate(vals):
            k = normalize_key(v)
            if any(normalize_key(x) in k for x in PRODUCT_COL_KEYWORDS):
                return j
    return 0


def build_day_col_map_from_rows(raw: pd.DataFrame, ym: str, candidate_rows: List[int]) -> Dict[int, pd.Timestamp]:
    day_map: Dict[int, pd.Timestamp] = {}
    for i in candidate_rows:
        if i is None or i < 0 or i >= len(raw):
            continue
        vals = raw.iloc[i].tolist()
        for j, v in enumerate(vals):
            if j in day_map:
                continue
            ts = parse_day_token(v, ym)
            if ts is not None:
                day_map[j] = ts
    return day_map


def read_csv_with_fallback(file_path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(file_path, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(file_path, low_memory=False)


def extract_from_excel(file_path: Path, ym: str) -> Tuple[pd.DataFrame, str]:
    raw = pd.read_excel(file_path, header=None, dtype=object)
    if raw.empty:
        return pd.DataFrame(), "Empty sheet"

    product_header_row = detect_product_header_row(raw, top_n=30)
    date_header_row = detect_date_header_row(raw, ym, top_n=30)
    product_col_idx = detect_product_col_idx(raw, product_header_row)

    candidate_rows: List[int] = []
    if date_header_row is not None:
        candidate_rows.append(date_header_row)
    if product_header_row is not None:
        candidate_rows.append(product_header_row)
    if date_header_row is not None:
        candidate_rows.append(date_header_row - 1)
        candidate_rows.append(date_header_row + 1)
    if product_header_row is not None:
        candidate_rows.append(product_header_row - 1)
        candidate_rows.append(product_header_row + 1)

    day_col_map = build_day_col_map_from_rows(raw, ym, candidate_rows)
    if not day_col_map:
        return pd.DataFrame(), "No detectable date columns from header rows"

    start_row_candidates = [x for x in [product_header_row, date_header_row] if x is not None]
    data_start = (max(start_row_candidates) + 1) if start_row_candidates else 1

    records: List[dict] = []
    for i in range(data_start, len(raw)):
        product_raw = normalize_text(raw.iat[i, product_col_idx] if product_col_idx < raw.shape[1] else "")
        if product_raw == "" or product_raw.lower() == "nan":
            continue
        if is_summary_product(product_raw):
            continue

        pname_norm = normalize_product_name(product_raw)
        for col_idx, ts in day_col_map.items():
            if col_idx >= raw.shape[1]:
                continue
            qty = pd.to_numeric(raw.iat[i, col_idx], errors="coerce")
            if pd.isna(qty):
                continue
            records.append(
                {
                    "ym": ym,
                    "date": ts.strftime("%Y-%m-%d"),
                    "product_name_raw": product_raw,
                    "product_name_norm": pname_norm,
                    "sales_qty": float(qty),
                }
            )

    if not records:
        return pd.DataFrame(), "No daily sales values extracted"
    return pd.DataFrame(records), f"excel parsed (product_header_row={product_header_row}, date_header_row={date_header_row})"


def extract_from_csv(file_path: Path, ym: str) -> Tuple[pd.DataFrame, str]:
    df = read_csv_with_fallback(file_path)
    if df.empty:
        return pd.DataFrame(), "Empty csv"

    product_col = None
    for c in df.columns:
        if any(normalize_key(x) in normalize_key(c) for x in PRODUCT_COL_KEYWORDS):
            product_col = c
            break
    if product_col is None:
        product_col = df.columns[0]

    day_cols: Dict[str, pd.Timestamp] = {}
    for c in df.columns:
        if c == product_col:
            continue
        if is_purchase_text(c):
            continue
        ts = parse_day_token(c, ym)
        if ts is not None:
            day_cols[str(c)] = ts

    if not day_cols:
        return pd.DataFrame(), "No detectable date columns in csv header"

    records: List[dict] = []
    for _, row in df.iterrows():
        product_raw = normalize_text(row[product_col])
        if product_raw == "" or product_raw.lower() == "nan" or is_summary_product(product_raw):
            continue
        pname_norm = normalize_product_name(product_raw)
        for col, ts in day_cols.items():
            qty = pd.to_numeric(row[col], errors="coerce")
            if pd.isna(qty):
                continue
            records.append(
                {
                    "ym": ym,
                    "date": ts.strftime("%Y-%m-%d"),
                    "product_name_raw": product_raw,
                    "product_name_norm": pname_norm,
                    "sales_qty": float(qty),
                }
            )

    if not records:
        return pd.DataFrame(), "No daily sales values extracted"
    return pd.DataFrame(records), "csv parsed"


def load_master() -> pd.DataFrame:
    if not PRODUCT_MASTER_REP_PATH.exists():
        raise FileNotFoundError(f"Missing required input: {PRODUCT_MASTER_REP_PATH}")
    master = pd.read_csv(PRODUCT_MASTER_REP_PATH, low_memory=False)
    cols = set(master.columns)
    if {"product_name_norm", "representative_plu_code", "representative_category"}.issubset(cols):
        out = master.rename(
            columns={
                "representative_plu_code": "plu_code",
                "representative_category": "product_category",
            }
        )[["product_name_norm", "plu_code", "product_category"]].copy()
    else:
        raise KeyError("Required columns not found in product_master_representative.csv")
    out["product_name_norm"] = out["product_name_norm"].map(normalize_product_name)
    out["plu_code"] = out["plu_code"].astype(str).str.strip()
    out["product_category"] = out["product_category"].astype(str).str.strip()
    out = out[(out["product_name_norm"] != "") & (out["plu_code"] != "")]
    return out.drop_duplicates(subset=["product_name_norm"], keep="first")


def month_date_range(ym: str) -> pd.DatetimeIndex:
    y = int(ym[:4])
    m = int(ym[5:7])
    last_day = calendar.monthrange(y, m)[1]
    return pd.date_range(f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last_day:02d}", freq="D")


def read_v1_success_count() -> int:
    if not V1_REPORT_PATH.exists():
        return 0
    text = V1_REPORT_PATH.read_text(encoding="utf-8")
    m = re.search(r"^success_files:\s*(\d+)\s*$", text, flags=re.MULTILINE)
    if not m:
        return 0
    return int(m.group(1))


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SALES_MONTHLY_DIR.exists():
        raise FileNotFoundError(f"Missing required input directory: {SALES_MONTHLY_DIR}")

    master = load_master()
    target_files = sorted(
        p for p in SALES_MONTHLY_DIR.rglob("*") if p.is_file() and p.suffix.lower() in TARGET_EXT
    )

    file_results: List[FileResult] = []
    all_daily: List[pd.DataFrame] = []
    monthly_products: Dict[str, pd.DataFrame] = {}
    unmatched_removed_rows = 0

    for fp in target_files:
        ym = extract_year_month(fp)
        if ym is None:
            file_results.append(FileResult(fp, False, "Failed to extract year-month"))
            continue
        try:
            if fp.suffix.lower() in {".xlsx", ".xls"}:
                daily_df, parse_msg = extract_from_excel(fp, ym)
            else:
                daily_df, parse_msg = extract_from_csv(fp, ym)

            if daily_df.empty:
                file_results.append(FileResult(fp, False, parse_msg))
                continue

            merged = daily_df.merge(master, on="product_name_norm", how="left")
            unmatched_removed_rows += int(merged["plu_code"].isna().sum())
            matched = merged.dropna(subset=["plu_code"]).copy()
            if matched.empty:
                file_results.append(FileResult(fp, False, "All rows unmatched to master"))
                continue

            matched["plu_code"] = matched["plu_code"].astype(str).str.strip()
            matched["product_category"] = matched["product_category"].astype(str).str.strip()
            matched["sales_qty"] = pd.to_numeric(matched["sales_qty"], errors="coerce").fillna(0.0)

            all_daily.append(
                matched[["ym", "date", "plu_code", "product_name_raw", "product_category", "sales_qty"]]
                .rename(columns={"product_name_raw": "product_name"})
            )

            prod_map = matched[["ym", "plu_code", "product_name_raw", "product_category"]].drop_duplicates()
            prod_map = prod_map.rename(columns={"product_name_raw": "product_name"})
            monthly_products[ym] = (
                pd.concat([monthly_products.get(ym, pd.DataFrame()), prod_map], ignore_index=True)
                .drop_duplicates()
            )
            file_results.append(FileResult(fp, True, parse_msg))
        except Exception as exc:
            file_results.append(FileResult(fp, False, str(exc)))

    if all_daily:
        daily = pd.concat(all_daily, ignore_index=True)
        daily = daily.groupby(["ym", "date", "plu_code", "product_name", "product_category"], as_index=False)["sales_qty"].sum()
    else:
        daily = pd.DataFrame(columns=["ym", "date", "plu_code", "product_name", "product_category", "sales_qty"])

    filled_chunks: List[pd.DataFrame] = []
    zero_filled_rows = 0
    for ym, prod_df in sorted(monthly_products.items()):
        prod_unique = prod_df[["plu_code", "product_name", "product_category"]].drop_duplicates()
        if prod_unique.empty:
            continue
        dates = month_date_range(ym).strftime("%Y-%m-%d")
        grid = prod_unique.assign(_k=1).merge(pd.DataFrame({"date": dates, "_k": 1}), on="_k").drop(columns="_k")
        grid["ym"] = ym
        merged_grid = grid.merge(
            daily[daily["ym"] == ym],
            on=["ym", "date", "plu_code", "product_name", "product_category"],
            how="left",
        )
        miss = int(merged_grid["sales_qty"].isna().sum())
        zero_filled_rows += miss
        merged_grid["sales_qty"] = merged_grid["sales_qty"].fillna(0.0)
        filled_chunks.append(merged_grid)

    if filled_chunks:
        final_df = pd.concat(filled_chunks, ignore_index=True)
        final_df = final_df[["date", "plu_code", "product_name", "product_category", "sales_qty"]]
    else:
        final_df = pd.DataFrame(columns=["date", "plu_code", "product_name", "product_category", "sales_qty"])

    final_df["sales_qty"] = pd.to_numeric(final_df["sales_qty"], errors="coerce").fillna(0.0)
    final_df = final_df.sort_values(["date", "plu_code"]).reset_index(drop=True)
    final_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    success_files = sum(1 for r in file_results if r.success)
    failed_files = len(file_results) - success_files
    v1_success = read_v1_success_count()
    added_success = success_files - v1_success

    if final_df.empty:
        date_min, date_max, plu_unique = "N/A", "N/A", 0
    else:
        date_min = str(final_df["date"].min())
        date_max = str(final_df["date"].max())
        plu_unique = int(final_df["plu_code"].nunique())

    lines: List[str] = []
    lines.append("Monthly Sales Converter V2 Report")
    lines.append(f"input_sales_monthly_dir: {SALES_MONTHLY_DIR.as_posix()}")
    lines.append(f"input_product_master_representative: {PRODUCT_MASTER_REP_PATH.as_posix()}")
    lines.append(f"processed_files: {len(target_files)}")
    lines.append(f"success_files: {success_files}")
    lines.append(f"failed_files: {failed_files}")
    lines.append(f"v1_success_files: {v1_success}")
    lines.append(f"additional_success_vs_v1: {added_success}")
    lines.append(f"final_rows: {len(final_df)}")
    lines.append(f"date_min: {date_min}")
    lines.append(f"date_max: {date_max}")
    lines.append(f"plu_code_unique_count: {plu_unique}")
    lines.append(f"unmatched_removed_rows: {unmatched_removed_rows}")
    lines.append(f"zero_filled_rows: {zero_filled_rows}")
    lines.append(f"output_csv: {OUTPUT_CSV.as_posix()}")
    lines.append("")
    lines.append("[Failed Files]")
    for r in file_results:
        if not r.success:
            rel = r.file_path.relative_to(BASE_DIR).as_posix()
            lines.append(f"- {rel} | {r.message}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Processed files: {len(target_files)}")
    print(f"Success files: {success_files}")
    print(f"Failed files: {failed_files}")
    print(f"Additional success vs v1: {added_success}")
    print(f"Final rows: {len(final_df)}")
    print(f"Date range: {date_min} ~ {date_max}")
    print(f"Unique plu_code: {plu_unique}")
    print(f"Unmatched removed rows: {unmatched_removed_rows}")
    print(f"Zero-filled rows: {zero_filled_rows}")
    print(f"Saved CSV: {OUTPUT_CSV}")
    print(f"Saved report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
