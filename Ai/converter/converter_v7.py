"""
converter.py - 일별 판매현황 xlsx/csv -> PLU 매칭 -> feature CSV/XLSX 변환기

터미널(로컬) 사용법
    python converter.py --sales <판매파일.xlsx|csv|디렉터리|glob|콤마목록> --master <분류기준표.csv|xlsx>
    python converter.py --sales "data/raw/*.xlsx" --master data/분류기준표.csv
    python converter.py --sales "a.xlsx,b.xlsx,c.xlsx" --master data/분류기준표.csv

Google Colab 사용법
    from converter import run
    run(
        sales="판매현황_2026_04_01.xlsx",
        master="분류기준표.csv",
        force=False,
        fuzzy_threshold=1.0,
    )

출력:
    data/processed/ms_sales_<date 또는 date_range>_features.csv
    data/processed/ms_sales_<date 또는 date_range>_unmatched.txt
"""

import argparse
import glob
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path
import re
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

# 소계/분류 행 필터
SKIP_ROWS = {
    "밥류",
    "도시락",
    "정찬도시락",
    "덮밥/초밥",
    "주문도시락",
    "김밥",
    "줄김밥",
    "용기/대용량김밥",
    "주먹밥",
    "일반삼각",
    "더큰삼각",
    "기타주먹밥",
}

SKIP_KEYWORDS = {"행사", "소계", "합계", "데이"}

HOUR_COLS = [f"{h:02d}H" for h in range(24)]  # 00H ~ 23H
MATCH_RESULT_COLS = [
    "PLU코드",
    "상품명",
    "카테고리힌트",
    "대분류",
    "중분류",
    "소분류",
    "매출합계",
    "__match_type",
]
OUTPUT_COLS = [
    "date",
    "plu_code",
    "product_name",
    "category_l",
    "category_m",
    "category_s",
    "sales",
    "lag_1",
    "lag_3",
    "lag_7",
    "rolling_7_mean",
    "rolling_7_std",
    "day_of_week",
    "month",
    "is_holiday",
    # ── 날씨 피처 (날씨 CSV 제공 시 실제 값, 미제공 시 기본값 0/NaN) ──
    "temp_avg",           # 평균기온(°C)
    "temp_min",           # 최저기온(°C)
    "temp_max",           # 최고기온(°C)
    "rainfall",           # 일강수량(mm), 비 없는 날 = 0.0
    "rain_yn",            # 강수 여부 (0=맑음, 1=비)
    # ── 외생변수 (Phase 2에서 실제 데이터로 교체 예정) ──
    "academic_event",
    "building_headcount",
    "safety_stock",
    "match_type",
]

KR_HOLIDAYS_FALLBACK = {
    2024: [
        "2024-01-01",
        "2024-02-09",
        "2024-02-10",
        "2024-02-11",
        "2024-02-12",
        "2024-03-01",
        "2024-04-10",
        "2024-05-05",
        "2024-05-06",
        "2024-05-15",
        "2024-06-06",
        "2024-08-15",
        "2024-09-16",
        "2024-09-17",
        "2024-09-18",
        "2024-10-01",
        "2024-10-03",
        "2024-10-09",
        "2024-12-25",
    ],
    2025: [
        "2025-01-01",
        "2025-01-27",
        "2025-01-28",
        "2025-01-29",
        "2025-01-30",
        "2025-03-01",
        "2025-03-03",
        "2025-05-05",
        "2025-05-06",
        "2025-06-03",
        "2025-06-06",
        "2025-08-15",
        "2025-10-03",
        "2025-10-05",
        "2025-10-06",
        "2025-10-07",
        "2025-10-08",
        "2025-10-09",
        "2025-12-25",
    ],
    2026: [
        "2026-01-01",
        "2026-02-16",
        "2026-02-17",
        "2026-02-18",
        "2026-03-01",
        "2026-03-02",
        "2026-05-05",
        "2026-05-24",
        "2026-05-25",
        "2026-06-03",
        "2026-06-06",
        "2026-07-17",
        "2026-08-15",
        "2026-08-17",
        "2026-09-24",
        "2026-09-25",
        "2026-09-26",
        "2026-10-03",
        "2026-10-05",
        "2026-10-09",
        "2026-12-25",
    ],
    2027: [
        "2027-01-01",
        "2027-02-06",
        "2027-02-07",
        "2027-02-08",
        "2027-02-09",
        "2027-03-01",
        "2027-05-05",
        "2027-05-13",
        "2027-06-06",
        "2027-07-17",
        "2027-08-15",
        "2027-08-16",
        "2027-09-14",
        "2027-09-15",
        "2027-09-16",
        "2027-10-03",
        "2027-10-04",
        "2027-10-09",
        "2027-10-11",
        "2027-12-25",
        "2027-12-27",
    ],
    2028: [
        "2028-01-01",
        "2028-01-26",
        "2028-01-27",
        "2028-01-28",
        "2028-03-01",
        "2028-04-12",
        "2028-05-02",
        "2028-05-05",
        "2028-06-06",
        "2028-07-17",
        "2028-08-15",
        "2028-10-02",
        "2028-10-03",
        "2028-10-04",
        "2028-10-05",
        "2028-10-09",
        "2028-12-25",
    ],
    2029: [
        "2029-01-01",
        "2029-02-12",
        "2029-02-13",
        "2029-02-14",
        "2029-03-01",
        "2029-05-05",
        "2029-05-07",
        "2029-05-20",
        "2029-05-21",
        "2029-06-06",
        "2029-07-17",
        "2029-08-15",
        "2029-09-21",
        "2029-09-22",
        "2029-09-23",
        "2029-09-24",
        "2029-10-03",
        "2029-10-09",
        "2029-12-25",
    ],
    2030: [
        "2030-01-01",
        "2030-02-02",
        "2030-02-03",
        "2030-02-04",
        "2030-02-05",
        "2030-03-01",
        "2030-04-03",
        "2030-05-05",
        "2030-05-06",
        "2030-05-09",
        "2030-06-06",
        "2030-06-12",
        "2030-07-17",
        "2030-08-15",
        "2030-09-11",
        "2030-09-12",
        "2030-09-13",
        "2030-10-03",
        "2030-10-09",
        "2030-12-25",
    ],
}


def normalize_name(name: str) -> str:
    """공백 제거 후 소문자 통일. 매칭 키로만 사용."""
    if not isinstance(name, str):
        return ""
    return re.sub(r"\s+", "", name.strip()).lower()


def normalize_plu(plu: str) -> str:
    """
    파일(xlsx/csv) 읽기 단계에서만 적용하는 PLU 정규화.
    - 문자열 기반으로 소수점/과학적표기법 정리
    - API 레이어에는 절대 적용하지 않음
    """
    if not isinstance(plu, str):
        return ""
    value = plu.strip()
    if not value:
        return ""

    # 과학적 표기법: 1.23e3 -> 1230 (Decimal로 float 정밀도 이슈 회피)
    sci_number = re.fullmatch(r"[+\-]?\d+(\.\d+)?[eE][+\-]?\d+", value)
    if sci_number:
        try:
            return str(int(Decimal(value)))
        except (InvalidOperation, ValueError, OverflowError):
            return value

    # 소수점 뒤 0만 있는 경우: 1234.0 -> 1234
    if re.fullmatch(r"[+\-]?\d+\.0+", value):
        return value.split(".", 1)[0]

    return value


def is_subtotal_row(name: str) -> bool:
    """명확한 소계/분류 행 판별."""
    if not isinstance(name, str):
        return True
    s = name.strip()
    if not s:
        return True

    if s in SKIP_ROWS:
        return True

    if any(keyword in s for keyword in SKIP_KEYWORDS):
        return True

    if re.search(r"\((대|중|소|상|하|컵.?대|컵.?소)\)", s):
        return True

    # 브랜드)상품명 구조가 없고 숫자도 없으면 분류/소계 가능성이 높음
    if ")" not in s and not re.search(r"\d", s):
        return True

    return False


def is_ambiguous_subtotal(name: str) -> bool:
    """1차 필터를 통과한 행 중 소계 패턴(예: 커피음료(RTD), 용기면(대)) 판별."""
    if not isinstance(name, str):
        return False
    s = name.strip()
    # 끝이 (한글|영문대문자|한글/한글)이고 숫자가 없으면 소계로 판단
    matched = re.search(r"\(([가-힣]+|[A-Z]+|[가-힣]+/[가-힣]+)\)$", s)
    return bool(matched and not re.search(r"\d", s))


def _find_header_row(df_probe: pd.DataFrame) -> int:
    for i, row in df_probe.iterrows():
        if any("PLU" in str(v).upper() for v in row.values):
            return int(i)
    return 0


def load_master(path: str) -> Tuple[pd.DataFrame, str, str]:
    """
    분류기준표 로드 (CSV 또는 xlsx).
    헤더 위치 자동 탐지, dtype=str 유지.
    필수 컬럼: PLU코드 계열, 상품명
    """
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        probe = pd.read_excel(path, header=None, nrows=10, dtype=str)
        header_row = _find_header_row(probe)
        df = pd.read_excel(path, header=header_row, dtype=str)
    else:
        probe = pd.read_csv(path, header=None, nrows=10, dtype=str, encoding="utf-8-sig")
        header_row = _find_header_row(probe)
        df = pd.read_csv(path, header=header_row, dtype=str, encoding="utf-8-sig")

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").copy()

    plu_col = next((c for c in df.columns if "PLU" in c.upper()), None)
    name_col = next((c for c in df.columns if "상품명" in c), None)
    if plu_col is None or name_col is None:
        raise ValueError(f"분류기준표에서 PLU 또는 상품명 컬럼을 찾을 수 없습니다.\n현재 컬럼: {list(df.columns)}")

    df[plu_col] = df[plu_col].fillna("").astype(str).map(normalize_plu)
    df[name_col] = df[name_col].fillna("").astype(str).str.strip()
    df["__norm_name"] = df[name_col].map(normalize_name)

    for col in ("대분류", "중분류", "소분류"):
        if col not in df.columns:
            df[col] = ""

    # 동일 정규화 상품명 중복 시 숫자 PLU가 더 큰 것을 우선 채택
    dup = df[df["__norm_name"].duplicated(keep=False) & (df["__norm_name"] != "")]
    if not dup.empty:
        print("\n[중복 상품명 감지]")
        for norm_name, grp in dup.groupby("__norm_name"):
            display_name = grp[name_col].iloc[0]
            cats = grp[["대분류", "중분류", "소분류"]].drop_duplicates()
            if len(cats) > 1:
                print(f"  ⚠ '{display_name}': 동일 상품명에 분류가 다릅니다.")
                print(cats.to_string(index=False))

    df["__plu_numeric"] = pd.to_numeric(df[plu_col], errors="coerce")
    df = df.sort_values(
        by=["__norm_name", "__plu_numeric", plu_col],
        ascending=[True, False, False],
        na_position="last",
    )
    df = df.drop_duplicates(subset=["__norm_name"], keep="first")
    df = df.drop(columns=["__plu_numeric"]).reset_index(drop=True)

    print(f"✅ 분류기준표 로드 완료: {len(df):,}개 상품")
    return df, plu_col, name_col


def load_sales(path: str) -> pd.DataFrame:
    """
    판매현황 xlsx/csv 로드 + 소계/분류 행 제거.
    지원 포맷:
    - 상세형: idx + 상품명 + 매출합계 + 매출평균 + 00H~23H
    - 요약형: 상품명 + 매입합계 + 매출합계 + 매출평균 + ...
    """
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        raw = pd.read_excel(path, header=None, dtype=str)
    else:
        raw = pd.read_csv(path, header=None, dtype=str, encoding="utf-8-sig")

    data = raw.iloc[5:].reset_index(drop=True)
    ncols = data.shape[1]

    if ncols < 7:
        raise ValueError(f"판매현황 파일 컬럼이 부족합니다 (최소 7, 현재 {ncols})")

    if ncols >= 28:
        # 상세형
        name_idx, sales_idx, avg_idx = 1, 2, 3
        hour_start = 4
    else:
        # 요약형
        name_idx, sales_idx, avg_idx = 0, 2, 3
        hour_start = None

    current_category = ""
    records: List[Dict[str, object]] = []

    for _, row in data.iterrows():
        name_raw = row.iloc[name_idx] if name_idx < len(row) else ""
        name = str(name_raw).strip() if pd.notna(name_raw) else ""
        if not name:
            continue

        if is_subtotal_row(name):
            # 카테고리 힌트로 사용할 값 보존
            if len(name) <= 20 and "(" not in name and ")" not in name:
                current_category = name
            continue

        if is_ambiguous_subtotal(name):
            continue

        sales_raw = row.iloc[sales_idx] if sales_idx < len(row) else 0
        avg_raw = row.iloc[avg_idx] if avg_idx < len(row) else 0
        sales = int(pd.to_numeric(sales_raw, errors="coerce")) if pd.notna(pd.to_numeric(sales_raw, errors="coerce")) else 0
        avg = int(pd.to_numeric(avg_raw, errors="coerce")) if pd.notna(pd.to_numeric(avg_raw, errors="coerce")) else 0

        record: Dict[str, object] = {
            "상품명": name,
            "카테고리힌트": current_category,
            "매출합계": sales,
            "매출평균": avg,
        }

        for i, hour_col in enumerate(HOUR_COLS):
            if hour_start is None or hour_start + i >= len(row):
                record[hour_col] = 0
            else:
                value = pd.to_numeric(row.iloc[hour_start + i], errors="coerce")
                record[hour_col] = int(value) if pd.notna(value) else 0

        records.append(record)

    data = pd.DataFrame(records)
    if data.empty:
        data = pd.DataFrame(columns=["상품명", "카테고리힌트", "매출합계", "매출평균", *HOUR_COLS])
    else:
        for col in ["매출합계", "매출평균"] + HOUR_COLS:
            data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).round().astype(int)

    print(f"✅ 판매현황 로드 완료: {len(data):,}개 상품")
    return data


def fuzzy_match(name: str, candidates: Sequence[str], threshold: float = 0.75) -> Optional[str]:
    """difflib 기반 퍼지 매칭."""
    if threshold >= 1.0:
        return None

    norm = normalize_name(name)
    if not norm:
        return None
    norm_cands = {normalize_name(c): c for c in candidates if normalize_name(c)}
    if not norm_cands:
        return None

    matches = get_close_matches(norm, list(norm_cands.keys()), n=1, cutoff=threshold)
    if matches:
        return norm_cands[matches[0]]

    best_score = 0.0
    best_cand = None
    for norm_cand, original in norm_cands.items():
        score = SequenceMatcher(None, norm, norm_cand).ratio()
        if score > best_score:
            best_score = score
            best_cand = original
    if best_score >= threshold:
        return best_cand
    return None


def match_products(
    sales: pd.DataFrame,
    master: pd.DataFrame,
    plu_col: str,
    name_col: str,
    fuzzy_threshold: float = 0.75,
) -> Tuple[pd.DataFrame, List[str], List[Tuple[str, str, str]]]:
    """
    판매현황 x 분류기준표 매칭.
    1차: 정규화 이름 exact
    2차: difflib fuzzy
    """
    master_lookup = {}
    for _, row in master.iterrows():
        key = row["__norm_name"]
        if key:
            master_lookup[key] = {
                "PLU코드": str(row[plu_col]).strip(),
                "대분류": str(row.get("대분류", "")).strip(),
                "중분류": str(row.get("중분류", "")).strip(),
                "소분류": str(row.get("소분류", "")).strip(),
                "원본상품명": str(row[name_col]).strip(),
            }

    candidates = [v["원본상품명"] for v in master_lookup.values()]
    results = []
    unmatched = []
    fuzzy_matched = []

    for _, srow in sales.iterrows():
        name = str(srow["상품명"]).strip()
        norm = normalize_name(name)

        if norm in master_lookup:
            m = master_lookup[norm]
            results.append(
                {
                    "PLU코드": m["PLU코드"],
                    "상품명": name,
                    "카테고리힌트": str(srow.get("카테고리힌트", "")).strip(),
                    "대분류": m["대분류"],
                    "중분류": m["중분류"],
                    "소분류": m["소분류"],
                    "매출합계": int(srow["매출합계"]),
                    "__match_type": "exact",
                }
            )
            continue

        fuzzy_cand = fuzzy_match(name, candidates, threshold=fuzzy_threshold)
        if fuzzy_cand:
            fuzzy_norm = normalize_name(fuzzy_cand)
            m = master_lookup[fuzzy_norm]
            score = SequenceMatcher(None, norm, fuzzy_norm).ratio()
            results.append(
                {
                    "PLU코드": m["PLU코드"],
                    "상품명": name,
                    "카테고리힌트": str(srow.get("카테고리힌트", "")).strip(),
                    "대분류": m["대분류"],
                    "중분류": m["중분류"],
                    "소분류": m["소분류"],
                    "매출합계": int(srow["매출합계"]),
                    "__match_type": f"fuzzy({score:.2f})->{fuzzy_cand}",
                }
            )
            fuzzy_matched.append((name, fuzzy_cand, f"{score:.2f}"))
        else:
            unmatched.append(name)

    return pd.DataFrame(results, columns=MATCH_RESULT_COLS), unmatched, fuzzy_matched


def report(
    df: pd.DataFrame,
    unmatched_items: List[Tuple[str, str]],
    fuzzy_items: List[Tuple[str, str, str, str]],
) -> bool:
    matched_total = len(df)
    n_exact = int((df["__match_type"] == "exact").sum()) if matched_total else 0
    n_fuzzy = int(df["__match_type"].astype(str).str.startswith("fuzzy").sum()) if matched_total else 0
    n_unmatched = len(unmatched_items)
    total = matched_total + n_unmatched

    def pct(count: int) -> str:
        return f"{(count / total * 100):.1f}%" if total else "0.0%"

    print("\n" + "=" * 55)
    print("  매칭 결과 보고")
    print("=" * 55)
    print(f"  총 상품 수       : {total:>5}개")
    print(f"  정확 매칭        : {n_exact:>5}개  ({pct(n_exact)})")
    print(f"  퍼지 매칭        : {n_fuzzy:>5}개  ({pct(n_fuzzy)})")
    print(f"  매칭 실패        : {n_unmatched:>5}개  ({pct(n_unmatched)})")
    print(f"  전체 매칭률      : {pct(total - n_unmatched)}")
    print("=" * 55)

    if total == 0:
        print("\n❌ 처리할 판매 데이터가 없습니다. 입력 파일 구조를 확인하세요.")
        return False

    if fuzzy_items:
        print("\n⚠ 퍼지 매칭 항목 (확인 권장):")
        for source_file, original, candidate, score in fuzzy_items[:50]:
            print(f"   [{source_file}] '{original}' -> '{candidate}' (유사도: {score})")
        if len(fuzzy_items) > 50:
            print(f"   ... 외 {len(fuzzy_items) - 50}건")

    if unmatched_items:
        print(f"\n❌ 매칭 실패 {len(unmatched_items)}개:")
        for source_file, item in unmatched_items[:100]:
            print(f"   [{source_file}] {item}")
        if len(unmatched_items) > 100:
            print(f"   ... 외 {len(unmatched_items) - 100}건")

        print("\n  해결 방법:")
        print("  1) 분류기준표에 해당 상품명을 추가")
        print("  2) --force 플래그를 사용해 미매칭 포함 저장")
        return False

    print("\n✅ 매칭 실패 0건 — feature CSV/XLSX 생성 가능")
    return True


def _parse_full_date_from_text(text: str) -> Optional[date]:
    # YYYYMMDD or YYYY_MM_DD
    for matched in re.finditer(r"((?:19|20)\d{2})[_\-]?(\d{2})[_\-]?(\d{2})", text):
        y, m, d = matched.groups()
        try:
            return date(int(y), int(m), int(d))
        except ValueError:
            continue

    # YYMMDD
    for matched in re.finditer(r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)", text):
        yy, mm, dd = matched.groups()
        try:
            return date(2000 + int(yy), int(mm), int(dd))
        except ValueError:
            continue

    return None


def _parse_mmdd_from_text(text: str) -> Optional[Tuple[int, int]]:
    for matched in re.finditer(r"(?<!\d)(\d{2})(\d{2})(?!\d)", text):
        mm, dd = int(matched.group(1)), int(matched.group(2))
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            return mm, dd
    return None


def _infer_year_from_ancestors(path: Path) -> Optional[int]:
    for parent in path.parents:
        name = parent.name
        # YYYYMM folder
        for matched in re.finditer(r"(?<!\d)((?:19|20)\d{2})[_\-]?(\d{2})(?!\d)", name):
            y, m = int(matched.group(1)), int(matched.group(2))
            if 1 <= m <= 12:
                return y
        # YYMM folder
        for matched in re.finditer(r"(?<!\d)(\d{2})(\d{2})(?!\d)", name):
            yy, mm = int(matched.group(1)), int(matched.group(2))
            if 1 <= mm <= 12:
                return 2000 + yy
    return None


def parse_sales_date(path: str) -> date:
    """
    날짜 추출 우선순위:
    1) 부모 폴더명(가까운 순)의 YYYYMMDD / YYMMDD
    2) 파일명의 YYYYMMDD / YYMMDD
    3) 파일명 MMDD + 부모 폴더에서 추론한 연도
    4) 실행일
    """
    p = Path(path)

    for parent in p.parents:
        found = _parse_full_date_from_text(parent.name)
        if found:
            return found

    found_in_file = _parse_full_date_from_text(p.stem)
    if found_in_file:
        return found_in_file

    mmdd = _parse_mmdd_from_text(p.stem)
    if mmdd:
        year = _infer_year_from_ancestors(p) or datetime.today().year
        mm, dd = mmdd
        try:
            return date(year, mm, dd)
        except ValueError:
            pass

    return datetime.today().date()


def is_sales_candidate(path: Path) -> bool:
    """판매현황 파일 후보 여부 판별."""
    path_str = str(path)
    if "분류기준표" in path_str:
        return False
    if "판매현황" in path_str:
        return True
    if _parse_full_date_from_text(path.stem):
        return True
    if _parse_mmdd_from_text(path.stem) and _infer_year_from_ancestors(path):
        return True
    for parent in path.parents:
        if _parse_full_date_from_text(parent.name):
            return True
    return False


def resolve_sales_paths(sales_arg: str) -> List[Path]:
    """
    sales 입력을 파일 리스트로 확장.
    지원:
    - 단일 파일
    - 디렉터리
    - glob
    - 콤마 구분 목록
    """
    tokens = [token.strip() for token in str(sales_arg).split(",") if token.strip()]
    if not tokens:
        return []

    paths: List[Path] = []
    for token in tokens:
        matched_paths: List[Path] = []

        if any(ch in token for ch in "*?[]"):
            matched_paths = [Path(p) for p in glob.glob(token)]
        else:
            p = Path(token)
            if p.is_dir():
                files: List[Path] = []
                for pattern in ("*.xlsx", "*.xls", "*.csv"):
                    files.extend(p.rglob(pattern))
                matched_paths = sorted(files)
            elif p.exists():
                matched_paths = [p]

        if not matched_paths:
            print(f"⚠ 판매 파일을 찾지 못했습니다: {token}")
            continue

        filtered_paths = [p for p in matched_paths if is_sales_candidate(p)]
        paths.extend(filtered_paths)

    dedup = {}
    for p in paths:
        dedup[str(p.resolve())] = p
    resolved = list(dedup.values())
    resolved.sort(key=lambda p: (parse_sales_date(str(p)), str(p)))
    return resolved


def _category_multiplier(category: str) -> float:
    """중분류 기준 안전재고 배율."""
    c = str(category).strip()
    if any(key in c for key in ("도시락", "김밥", "삼각김밥", "밥류", "주먹밥")):
        return 0.3
    if any(key in c for key in ("음료", "과자", "캔디")):
        return 0.5
    if "담배" in c:
        return 1.0
    return 0.3


def _get_kr_holiday_set(years: Sequence[int]) -> set[pd.Timestamp]:
    """한국 공휴일(대체공휴일 포함) 집합을 반환."""
    year_list = sorted({int(y) for y in years})
    if not year_list:
        return set()

    try:
        import holidays as holidays_lib

        kr_holidays = holidays_lib.KR(years=year_list)
        return {pd.Timestamp(day).normalize() for day in kr_holidays.keys()}
    except Exception:
        holiday_set: set[pd.Timestamp] = set()
        for year in year_list:
            for iso_date in KR_HOLIDAYS_FALLBACK.get(year, []):
                holiday_set.add(pd.Timestamp(iso_date).normalize())
        return holiday_set


def _build_daily_base(matched_df: pd.DataFrame, sales_date: date) -> pd.DataFrame:
    """매칭 결과를 feature 생성용 일자 스키마로 변환."""
    base = matched_df.copy()
    base["date"] = pd.Timestamp(sales_date)
    base["plu_code"] = base["PLU코드"].fillna("").astype(str).str.strip()
    base["product_name"] = base["상품명"].fillna("").astype(str).str.strip()
    base["category_hint"] = base["카테고리힌트"].fillna("").astype(str).str.strip()
    base["category_l"] = base["대분류"].fillna("").astype(str).str.strip()
    base["category_m"] = base["중분류"].fillna("").astype(str).str.strip()
    base["category_s"] = base["소분류"].fillna("").astype(str).str.strip()
    base["sales"] = pd.to_numeric(base["매출합계"], errors="coerce").fillna(0).astype(int)
    base["match_type"] = base["__match_type"].fillna("exact").astype(str)
    return base[
        [
            "date",
            "plu_code",
            "product_name",
            "category_hint",
            "category_l",
            "category_m",
            "category_s",
            "sales",
            "match_type",
        ]
    ]


def _build_calendar_lag_features(history_df: pd.DataFrame) -> pd.DataFrame:
    """
    plu_code별 일자 시계열을 일 단위로 재색인한 뒤 lag/rolling 계산.
    - 누락 일자는 판매량 0으로 간주
    - lag_n은 'n일 전 같은 날짜' 기준
    """
    outputs: List[pd.DataFrame] = []
    for plu_code, group in history_df.groupby("plu_code", dropna=False):
        ordered = group.sort_values("date")[["date", "sales"]].copy()
        full_dates = pd.date_range(start=ordered["date"].min(), end=ordered["date"].max(), freq="D")
        series = ordered.set_index("date")["sales"].reindex(full_dates, fill_value=0.0).astype(float)

        frame = pd.DataFrame(
            {
                "date": full_dates,
                "plu_code": plu_code,
                "lag_1": series.shift(1),
                "lag_3": series.shift(3),
                "lag_7": series.shift(7),
                "rolling_7_mean": series.shift(1).rolling(window=7, min_periods=1).mean(),
                "rolling_7_std": series.shift(1).rolling(window=7, min_periods=1).std(ddof=0),
            }
        )
        outputs.append(frame)

    if not outputs:
        return pd.DataFrame(columns=["date", "plu_code", "lag_1", "lag_3", "lag_7", "rolling_7_mean", "rolling_7_std"])
    return pd.concat(outputs, ignore_index=True)


def build_feature_output(daily_frames: List[pd.DataFrame]) -> pd.DataFrame:
    """누적 일별 데이터를 확장 feature 스키마로 변환."""
    if not daily_frames:
        return pd.DataFrame(columns=OUTPUT_COLS)

    df = pd.concat(daily_frames, ignore_index=True)
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLS)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLS)

    for col in ("plu_code", "product_name", "category_hint", "category_l", "category_m", "category_s", "match_type"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0).astype(float)

    # 저장 직전 동일키 단일화 가드 (중복 배수 집계 방지)
    def _match_rank(match_type: str) -> int:
        t = str(match_type).lower()
        if t == "exact":
            return 0
        if t.startswith("fuzzy"):
            return 2
        return 1

    df["__match_rank"] = df["match_type"].map(_match_rank)
    df = df.sort_values(
        by=["date", "plu_code", "product_name", "__match_rank", "sales"],
        ascending=[True, True, True, True, False],
    )
    df = df.drop_duplicates(subset=["date", "plu_code", "product_name"], keep="first").copy()
    df = df.drop(columns=["__match_rank"])

    # 대/중/소분류 fallback: category_hint -> 기타
    for col in ("category_l", "category_m", "category_s"):
        empty_mask = df[col] == ""
        df.loc[empty_mask, col] = df.loc[empty_mask, "category_hint"]
        df.loc[df[col] == "", col] = "기타"

    # lag/rolling은 plu_code+date 기준으로 계산
    history_df = df.groupby(["date", "plu_code"], as_index=False)["sales"].sum()
    lag_features = _build_calendar_lag_features(history_df)
    df = df.merge(lag_features, on=["date", "plu_code"], how="left")

    for col in ("lag_1", "lag_3", "lag_7", "rolling_7_mean", "rolling_7_std"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    dt = df["date"]
    # 요일 인코딩 고정: 월=0, 화=1, 수=2, 목=3, 금=4, 토=5, 일=6
    df["day_of_week"] = dt.dt.weekday.astype(int)
    df["month"] = dt.dt.month.astype(int)

    # 외생 변수 기본값
    years = dt.dt.year.dropna().astype(int).unique().tolist()
    holiday_set = _get_kr_holiday_set(years)
    # 한국 공휴일 또는 주말(토/일)인 경우 1
    is_public_holiday = dt.dt.normalize().isin(holiday_set)
    is_weekend = dt.dt.dayofweek >= 5
    df["is_holiday"] = (is_public_holiday | is_weekend).astype(int)
    df["academic_event"] = 0
    df["building_headcount"] = 0

    safety_category = df["category_m"].copy()
    safety_category = safety_category.where(safety_category.str.strip() != "", df["category_l"])
    safety_category = safety_category.where(safety_category.str.strip() != "", df["category_hint"])
    safety_category = safety_category.where(safety_category.str.strip() != "", "기타")
    multipliers = safety_category.map(_category_multiplier)
    df["safety_stock"] = (df["rolling_7_mean"] * multipliers).round().clip(lower=0).fillna(0).astype(int)

    # 형식 정리
    df["sales"] = df["sales"].round().astype(int)
    df["lag_1"] = df["lag_1"].round().astype(int)
    df["lag_3"] = df["lag_3"].round().astype(int)
    df["lag_7"] = df["lag_7"].round().astype(int)
    df["rolling_7_mean"] = df["rolling_7_mean"].round(2)
    df["rolling_7_std"] = df["rolling_7_std"].round(2)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["match_type"] = df["match_type"].replace("", "exact")

    return df[OUTPUT_COLS].copy()


def _output_date_label(sales_paths: List[Path]) -> str:
    dates = sorted({parse_sales_date(str(path)).strftime("%Y_%m_%d") for path in sales_paths})
    if not dates:
        return datetime.today().strftime("%Y_%m_%d")
    if len(dates) == 1:
        return dates[0]
    return f"{dates[0]}_to_{dates[-1]}"


def save_outputs(
    raw_result_df: pd.DataFrame,
    daily_frames: List[pd.DataFrame],
    sales_paths: List[Path],
    unmatched_items: List[Tuple[str, str]],
    force: bool,
    output_dir: str = "data/processed",
    save_xlsx: bool = False,
    weather_df: Optional[pd.DataFrame] = None,
) -> Optional[Tuple[Path, Optional[Path]]]:
    """
    최종 feature CSV/XLSX 저장.
    미매칭 존재 + force=False면 저장 중단.
    weather_df 제공 시 날짜 기준 조인하여 날씨 피처 추가.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    label = _output_date_label(sales_paths)
    base = out_dir / f"ms_sales_{label}_features"
    csv_path = base.with_suffix(".csv")
    xlsx_path = base.with_suffix(".xlsx")
    unmatch_path = out_dir / f"ms_sales_{label}_unmatched.txt"

    if unmatched_items:
        with open(unmatch_path, "w", encoding="utf-8") as file:
            file.write(f"# 미매칭 항목 - {label}\n")
            for source_file, item in unmatched_items:
                file.write(f"[{source_file}] {item}\n")
        print(f"\n📄 미매칭 목록 저장: {unmatch_path}")

    if unmatched_items and not force:
        print("❌ 미매칭 항목이 존재하여 feature CSV/XLSX를 생성하지 않습니다.")
        print("   --force 플래그를 사용하면 미매칭 포함 저장합니다.")
        return None

    feature_df = build_feature_output(daily_frames)
    if feature_df.empty:
        print("❌ 생성된 feature 데이터가 없습니다. 입력 파일을 확인하세요.")
        return None

    # ── 날씨 조인 ──
    feature_df = _join_weather(feature_df, weather_df)

    feature_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 feature CSV 저장: {csv_path}")
    if save_xlsx:
        feature_df.to_excel(xlsx_path, index=False)
        print(f"💾 feature XLSX 저장: {xlsx_path}")
    print(f"   총 {len(feature_df):,}행")

    # force=True 상태에서 raw_result_df가 완전히 비어있지는 않은지 정보 제공
    if raw_result_df.empty:
        print("⚠ 참고: 매칭 결과 데이터프레임은 비어 있습니다.")
    return csv_path, (xlsx_path if save_xlsx else None)



def load_weather(weather_path: str) -> pd.DataFrame:
    """
    날씨 CSV 로드 및 정제.

    기상청 형식 컬럼:
      지점, 지점명, 일시, 평균기온(°C), 최저기온(°C), 최고기온(°C), 일강수량(mm)

    반환 DataFrame 컬럼:
      date, temp_avg, temp_min, temp_max, rainfall, rain_yn

    처리 규칙:
      - 일강수량 NaN → 0.0 (비 안 온 날)
      - rain_yn: 강수량 > 0 이면 1, 아니면 0
      - 평균기온/최저기온/최고기온 NaN → 전후일 평균으로 선형 보간
    """
    path = Path(weather_path)
    if not path.exists():
        raise FileNotFoundError(f"날씨 파일을 찾을 수 없습니다: {weather_path}")

    # 인코딩 자동 탐지 (기상청 csv는 cp949)
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            df = pd.read_csv(weather_path, dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"날씨 파일 인코딩을 인식할 수 없습니다: {weather_path}")

    df.columns = [str(c).strip() for c in df.columns]

    # 날짜 컬럼 탐지 (기상청: '일시')
    date_col = next(
        (c for c in df.columns if "일시" in c or "날짜" in c or "date" in c.lower()), None
    )
    if date_col is None:
        raise ValueError(f"날씨 파일에서 날짜 컬럼을 찾을 수 없습니다.\n현재 컬럼: {list(df.columns)}")

    # 기온/강수 컬럼 탐지
    def _find_col(keywords):
        for kw in keywords:
            found = next((c for c in df.columns if kw in c), None)
            if found:
                return found
        return None

    col_avg  = _find_col(["평균기온", "기온"])
    col_min  = _find_col(["최저기온"])
    col_max  = _find_col(["최고기온"])
    col_rain = _find_col(["일강수량", "강수량", "강수"])

    if col_avg is None:
        raise ValueError(f"날씨 파일에서 기온 컬럼을 찾을 수 없습니다.\n현재 컬럼: {list(df.columns)}")

    # 날짜 파싱
    df["date"] = pd.to_datetime(df[date_col].str.strip(), errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["date"]).copy()

    # 수치 변환
    for src, dest in [(col_avg, "temp_avg"), (col_min, "temp_min"), (col_max, "temp_max")]:
        if src:
            df[dest] = pd.to_numeric(df[src], errors="coerce")
        else:
            df[dest] = float("nan")

    if col_rain:
        df["rainfall"] = pd.to_numeric(df[col_rain], errors="coerce").fillna(0.0)
    else:
        df["rainfall"] = 0.0

    # 기온 결측 선형 보간 (전후일 평균)
    for col in ("temp_avg", "temp_min", "temp_max"):
        df[col] = df[col].interpolate(method="linear", limit_direction="both").round(1)

    # 강수 여부
    df["rain_yn"] = (df["rainfall"] > 0).astype(int)

    result = df[["date", "temp_avg", "temp_min", "temp_max", "rainfall", "rain_yn"]].copy()
    result = result.drop_duplicates(subset=["date"]).reset_index(drop=True)

    print(f"  ✅ 날씨 데이터 로드 완료: {len(result):,}일 ({result['date'].min()} ~ {result['date'].max()})")
    return result


def _join_weather(feature_df: pd.DataFrame, weather_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    features DataFrame에 날씨 피처 조인.

    날씨 데이터 있을 때:
      date 기준 LEFT JOIN → 날씨 컬럼 실제 값 사용
      매칭 안 되는 날짜: temp_avg/min/max = NaN, rainfall = 0.0, rain_yn = 0

    날씨 데이터 없을 때:
      모든 날씨 컬럼 기본값(0 또는 NaN) 채움

    [처리 규칙]
      - rainfall NaN → 0.0  (비 없는 날)
      - temp 계열 NaN → 0.0 (미제공 구간)
      - rain_yn: rainfall > 0 이면 1, 아니면 0
    """
    WEATHER_COLS = ["temp_avg", "temp_min", "temp_max", "rainfall", "rain_yn"]

    if weather_df is not None and not weather_df.empty:
        # date 컬럼 타입 통일 후 merge
        feature_df = feature_df.copy()
        weather_df = weather_df.copy()
        feature_df["date"] = feature_df["date"].astype(str).str.strip()
        weather_df["date"] = weather_df["date"].astype(str).str.strip()

        feature_df = feature_df.merge(
            weather_df[["date"] + WEATHER_COLS],
            on="date",
            how="left",
        )

        # 매칭 안 된 날짜 기본값 처리
        feature_df["rainfall"] = feature_df["rainfall"].fillna(0.0)
        for col in ("temp_avg", "temp_min", "temp_max"):
            feature_df[col] = feature_df[col].fillna(0.0)
        feature_df["rain_yn"] = (feature_df["rainfall"] > 0).astype(int)

        # 매칭률 출력
        matched_dates = feature_df["date"].isin(weather_df["date"])
        unique_dates = feature_df["date"].nunique()
        matched_unique = feature_df[matched_dates]["date"].nunique()
        print(f"  날씨 조인 완료: {matched_unique}/{unique_dates}일 매칭")

    else:
        # 날씨 파일 미제공 → 전체 기본값
        for col in ("temp_avg", "temp_min", "temp_max", "rainfall"):
            feature_df[col] = 0.0
        feature_df["rain_yn"] = 0
        print("  날씨 기본값 적용 (temp=0.0, rainfall=0.0, rain_yn=0)")

    # 컬럼 순서 OUTPUT_COLS 기준 정렬
    final_cols = [c for c in OUTPUT_COLS if c in feature_df.columns]
    return feature_df[final_cols].copy()

def run(
    sales: str,
    master: str,
    force: bool = False,
    fuzzy_threshold: float = 1.0,
    output_dir: str = "data/processed",
    save_xlsx: bool = False,
    weather: Optional[str] = None,
) -> Optional[Tuple[Path, Optional[Path]]]:
    """
    터미널/Colab 공용 진입점.

    Parameters
    ----------
    sales           : 판매현황 파일 경로/디렉터리/glob/콤마 목록
    master          : 분류기준표 csv/xlsx 경로
    force           : True면 미매칭 포함 강제 저장
    fuzzy_threshold : 퍼지 매칭 임계값
    output_dir      : 산출물 저장 경로
    save_xlsx       : True면 XLSX도 함께 저장
    weather         : 날씨 CSV 파일 경로 (선택, 없으면 날씨 컬럼 기본값 0 처리)
    """
    if not Path(master).exists():
        print(f"❌ 분류기준표 파일을 찾을 수 없습니다: {master}")
        return None

    sales_paths = resolve_sales_paths(sales)
    if not sales_paths:
        print(f"❌ 판매 파일을 찾을 수 없습니다: {sales}")
        return None

    print("\n📂 판매 파일 목록")
    for path in sales_paths:
        print(f"   - {path}")
    print(f"📂 분류기준표: {master}")
    print(f"   퍼지 매칭 임계값: {fuzzy_threshold}")

    master_df, plu_col, name_col = load_master(master)

    # 날씨 데이터 로드 (선택)
    weather_df: Optional[pd.DataFrame] = None
    if weather:
        print(f"\n[날씨] 날씨 데이터 로드 중...")
        try:
            weather_df = load_weather(weather)
        except Exception as e:
            print(f"  ⚠ 날씨 로드 실패: {e} → 날씨 컬럼은 기본값으로 처리")
            weather_df = None
    else:
        print("\n[날씨] 날씨 파일 미제공 → 날씨 컬럼 기본값(0) 처리")

    all_results = []
    daily_feature_frames = []
    unmatched_items: List[Tuple[str, str]] = []
    fuzzy_items: List[Tuple[str, str, str, str]] = []

    for sales_path in sales_paths:
        print(f"\n[처리 시작] {sales_path}")
        sales_df = load_sales(str(sales_path))
        result_df, unmatched, fuzzy_matched = match_products(
            sales=sales_df,
            master=master_df,
            plu_col=plu_col,
            name_col=name_col,
            fuzzy_threshold=fuzzy_threshold,
        )
        result_df["__source_file"] = sales_path.name
        all_results.append(result_df)

        sales_date = parse_sales_date(str(sales_path))
        daily_feature_frames.append(_build_daily_base(result_df, sales_date))

        unmatched_items.extend((sales_path.name, item) for item in unmatched)
        fuzzy_items.extend((sales_path.name, orig, cand, score) for (orig, cand, score) in fuzzy_matched)

    merged = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame(columns=["__match_type"])
    can_save = report(merged, unmatched_items, fuzzy_items)

    if can_save or force:
        return save_outputs(
            merged,
            daily_feature_frames,
            sales_paths,
            unmatched_items,
            force,
            output_dir=output_dir,
            save_xlsx=save_xlsx,
            weather_df=weather_df,
        )

    print("\n미매칭 항목을 해결한 뒤 다시 실행하거나, force=True로 강제 저장하세요.")
    return None


def _is_colab() -> bool:
    """Google Colab / IPython 커널 환경 감지."""
    try:
        shell = get_ipython().__class__.__name__  # type: ignore[name-defined]  # noqa
        return "ZMQ" in shell or "Colab" in shell or "Terminal" not in shell
    except NameError:
        return False


def main() -> None:
    if _is_colab():
        print("=" * 60)
        print("Google Colab / Jupyter 환경이 감지되었습니다.")
        print("argparse 대신 run() 함수를 직접 호출하세요.\n")
        print("사용 예시:")
        print("    from converter import run")
        print('    run(sales="판매현황_2026_04_01.xlsx", master="분류기준표.csv")')
        print("=" * 60)
        return

    parser = argparse.ArgumentParser(
        description="판매현황 파일 -> PLU 매칭 -> feature CSV/XLSX 변환기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sales",
        required=True,
        help="판매파일 경로/디렉터리/glob/콤마목록",
    )
    parser.add_argument("--master", required=True, help="분류기준표 csv/xlsx 경로")
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="결과 저장 폴더 (기본: data/processed)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="미매칭 항목이 있어도 매칭 성공 데이터만 강제 저장",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=1.0,
        help="퍼지 매칭 유사도 임계값 (기본: 1.0, exact-only)",
    )
    parser.add_argument(
        "--with-xlsx",
        action="store_true",
        help="CSV와 함께 XLSX도 저장",
    )
    parser.add_argument(
        "--weather",
        default=None,
        help="날씨 CSV 파일 경로 (선택, 기상청 형식: 일시/평균기온/최저기온/최고기온/일강수량)",
    )
    args = parser.parse_args()

    run(
        sales=args.sales,
        master=args.master,
        force=args.force,
        fuzzy_threshold=args.fuzzy_threshold,
        output_dir=args.output_dir,
        save_xlsx=args.with_xlsx,
        weather=args.weather,
    )


if __name__ == "__main__" and not _is_colab():
    main()
