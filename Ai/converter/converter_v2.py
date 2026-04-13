"""
converter_v2.py  ─  이마트24 판매현황 xlsx → RF 학습용 feature CSV 변환기
=============================================================================
[실제 파일 구조 기반 | PLU 매칭 완전 구현 버전]

◎ 분류기준표 파일 구조 (csv_상품분류기준표 폴더의 CSV 14개)
  row 0~2: 타이틀/빈행
  row 3  : 실제 헤더  [No | PLU코드 | 상품명 | 출력여부 | 대분류 | 중분류 | 소분류]
  row 4~ : 상품 데이터

◎ 판매현황 파일 구조 (이마트24 운영 플랫폼 수기 추출)
  row 0~4: 타이틀/헤더
  row 5~ : 데이터 행 (소계 + 실제 상품 혼재)
  col 0=상품명, col 2=매출합계(sales)

◎ 매칭 전략 (3단계)
  1단계: 정규화 Exact 매칭 (공백제거+소문자)     → 97.5% 처리
  2단계: 대소문자/특수문자 변형 매칭             → 추가 처리
  3단계: Fuzzy 매칭 (threshold=0.82, 보수적)   → 신중하게 적용
  미매칭: plu_code='' 로 기록, 별도 리포트 저장  → 억지 매칭 금지

◎ 사용법
  [터미널/VSCode]
    # 단일 날짜 폴더
    python converter_v2.py --input data/raw/240501-15 --master csv_상품분류기준표

    # 여러 폴더 동시 처리 (콤마 구분)
    python converter_v2.py --input "data/raw/240501-15,data/raw/240601-30" --master csv_상품분류기준표

  [Google Colab]
    from converter_v2 import run
    run(input_dir='240501-15', master_dir='csv_상품분류기준표', output_dir='data/processed')
=============================================================================
"""

import argparse
import glob
import os
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd


# ══════════════════════════════════════════════
# ① 상수 및 설정
# ══════════════════════════════════════════════

# 소계행 필터 키워드
SKIP_KEYWORDS: Set[str] = {"행사", "소계", "합계", "데이"}

# 카테고리별 안전재고 배율 (중분류/대분류 키워드 기준)
SAFETY_MULTIPLIERS: List[Tuple[str, float]] = [
    # (키워드, 배율) — 위에서부터 순서대로 매칭, 첫 번째 매칭 적용
    ("담배", 1.0),
    ("음료", 0.5), ("과자", 0.5), ("캔디", 0.5), ("초콜릿", 0.5),
    ("초콜렛", 0.5), ("젤리", 0.5), ("유제품", 0.5), ("커피", 0.5),
    ("생수", 0.5), ("스낵", 0.5), ("껌", 0.5),
    ("도시락", 0.3), ("김밥", 0.3), ("삼각", 0.3), ("밥류", 0.3),
    ("주먹밥", 0.3), ("빵", 0.3), ("샌드위치", 0.3), ("햄버거", 0.3),
    ("간편식품", 0.3), ("즉석식", 0.3),
]

# RF 학습 출력 컬럼 순서
OUTPUT_COLS = [
    "date", "plu_code", "product_name",
    "category_l", "category_m", "category_s",
    "sales",
    "lag_1", "lag_3", "lag_7",
    "rolling_7_mean", "rolling_7_std",
    "day_of_week", "month", "is_holiday",
    "academic_event", "building_headcount",
    "safety_stock",
    "match_type",  # 매칭 방법 추적용 (exact/fuzzy/unmatched)
]

# 한국 공휴일 (대체공휴일 포함, 2024~2026)
KR_HOLIDAYS = {
    2024: [
        "2024-01-01","2024-02-09","2024-02-10","2024-02-11","2024-02-12",
        "2024-03-01","2024-04-10","2024-05-05","2024-05-06","2024-05-15",
        "2024-06-06","2024-08-15","2024-09-16","2024-09-17","2024-09-18",
        "2024-10-01","2024-10-03","2024-10-09","2024-12-25",
    ],
    2025: [
        "2025-01-01","2025-01-27","2025-01-28","2025-01-29","2025-01-30",
        "2025-03-01","2025-03-03","2025-05-05","2025-05-06","2025-06-03",
        "2025-06-06","2025-08-15","2025-10-03","2025-10-05","2025-10-06",
        "2025-10-07","2025-10-08","2025-10-09","2025-12-25",
    ],
    2026: [
        "2026-01-01","2026-02-16","2026-02-17","2026-02-18",
        "2026-03-01","2026-03-02","2026-05-05","2026-05-24","2026-05-25",
        "2026-06-03","2026-06-06","2026-07-17","2026-08-15","2026-08-17",
        "2026-09-24","2026-09-25","2026-09-26",
        "2026-10-03","2026-10-05","2026-10-09","2026-12-25",
    ],
}


# ══════════════════════════════════════════════
# ② 유틸리티 함수
# ══════════════════════════════════════════════

def normalize_plu(plu: str) -> str:
    """
    xlsx 읽기 단계 전용 PLU 정규화.
    Excel float 변환 문제 처리:
      '88011158.0' → '88011158'
      '8.8e7'      → '88000000'
    ※ FastAPI API 수신 레이어에는 절대 사용 안 함 (Spring Boot에서 String 보장)
    """
    if not isinstance(plu, str):
        return ""
    value = plu.strip()
    if not value or value.lower() in ("nan", "none", ""):
        return ""
    # 과학적 표기법 처리
    if re.fullmatch(r"[+\-]?\d+(\.\d+)?[eE][+\-]?\d+", value):
        try:
            return str(int(Decimal(value)))
        except (InvalidOperation, ValueError, OverflowError):
            return value
    # '12345.0' 형태 처리
    if re.fullmatch(r"[+\-]?\d+\.0+", value):
        return value.split(".", 1)[0]
    return value


def normalize_name(name: str) -> str:
    """
    상품명 정규화 (매칭 키 생성용).
    1. 공백 전체 제거
    2. 소문자 변환
    3. 유니코드 NFKC 정규화 (전각/반각 통일)
    예: 'CJ )햇반  치킨마요' → 'cj)햇반치킨마요'
    """
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKC", name.strip())
    s = re.sub(r"\s+", "", s)
    return s.lower()


def normalize_name_loose(name: str) -> str:
    """
    느슨한 정규화 (2단계 매칭용).
    추가로 특수문자(괄호, 점, 슬래시 등)도 제거.
    예: 'CJ)햇반(치킨마요)' → 'cj햇반치킨마요'
    """
    s = normalize_name(name)
    s = re.sub(r"[()./\-_&\[\]{}%@#*!?+~]", "", s)
    return s


def get_holiday_set(years: List[int]) -> set:
    """연도 목록에 대한 공휴일 날짜 집합 반환."""
    try:
        import holidays as holidays_lib
        kr = holidays_lib.KR(years=years)
        return {pd.Timestamp(d).normalize() for d in kr.keys()}
    except Exception:
        pass
    result = set()
    for y in years:
        for iso_str in KR_HOLIDAYS.get(y, []):
            result.add(pd.Timestamp(iso_str).normalize())
    return result


def parse_date_from_foldername(folder_name: str) -> Optional[date]:
    """폴더명에서 날짜 추출. '240502판매현황' → date(2024, 5, 2)"""
    m = re.search(r"(\d{6})", folder_name)
    if m:
        s = m.group(1)
        try:
            return date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
        except ValueError:
            pass
    return None


def parse_date_from_filename(path: str) -> Optional[date]:
    """파일명에서 날짜 추출."""
    stem = Path(path).stem
    m = re.search(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})", stem)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r"(\d{6})", stem)
    if m:
        s = m.group(1)
        try:
            return date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
        except ValueError:
            pass
    return None


def safety_stock_multiplier(category: str) -> float:
    """카테고리 키워드 기반 안전재고 배율 반환."""
    cat = str(category).strip()
    for keyword, mult in SAFETY_MULTIPLIERS:
        if keyword in cat:
            return mult
    return 0.3


def is_subtotal_row(name: str) -> bool:
    """
    소계행 여부 판별.
    실제 상품: '브랜드)상품명' 구조 → ')' 포함
    소계행: 카테고리명만 있는 행 또는 중간집계 행
    """
    if not name or pd.isna(name):
        return True
    s = str(name).strip()
    if not s or s.lower() in ("nan", "none"):
        return True

    # SKIP 키워드 포함
    for kw in SKIP_KEYWORDS:
        if kw in s:
            return True

    # (대)/(중)/(소) 패턴 → 중간집계
    if re.search(r"\((대|중|소|상|하|컵.?대|컵.?소)\)", s):
        return True

    # ')' 없으면 소계 (브랜드 구분자 없음)
    if ")" not in s:
        return True

    return False


# ══════════════════════════════════════════════
# ③ 분류기준표 로드 (핵심: PLU 매칭 테이블 생성)
# ══════════════════════════════════════════════

def load_master(master_path: str) -> Dict[str, dict]:
    """
    분류기준표 로드 → 3단계 매칭 테이블 생성.

    지원 입력 형식:
      - 폴더 경로: 폴더 안의 CSV 14개 전부 읽어서 통합
      - 단일 CSV/xlsx 파일 경로

    반환: {정규화_상품명: {plu_code, product_name, cat_l, cat_m, cat_s}} 딕셔너리

    중복 상품명 처리 전략:
      같은 정규화 이름에 PLU 여러 개 → 13자리 EAN 우선, 그 다음 숫자 큰 것 우선
      (PLU 코드 자체는 모두 저장해서 참조 가능하게 유지)
    """
    path = Path(master_path)

    # CSV 파일 목록 수집
    csv_files = []
    if path.is_dir():
        csv_files = sorted(path.glob("*.csv")) + sorted(path.glob("*.xlsx"))
        if not csv_files:
            # 하위 폴더 재귀 탐색
            csv_files = sorted(path.rglob("*.csv")) + sorted(path.rglob("*.xlsx"))
    elif path.exists():
        csv_files = [path]

    if not csv_files:
        raise FileNotFoundError(f"분류기준표 파일을 찾을 수 없습니다: {master_path}")

    print(f"  분류기준표 파일 {len(csv_files)}개 로드 중...")

    all_dfs = []
    for fpath in csv_files:
        df = _read_master_file(str(fpath))
        if df is not None and not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        raise ValueError("분류기준표에서 유효한 데이터를 읽지 못했습니다.")

    master = pd.concat(all_dfs, ignore_index=True)

    # 컬럼명 정리
    master.columns = [str(c).strip() for c in master.columns]

    # 필수 컬럼 확인
    required = ["PLU코드", "상품명"]
    for col in required:
        if col not in master.columns:
            raise ValueError(
                f"분류기준표에 '{col}' 컬럼이 없습니다.\n"
                f"현재 컬럼: {list(master.columns)}"
            )

    # 유효 데이터만 유지
    master = master.dropna(subset=["PLU코드", "상품명"]).copy()
    master["PLU코드"] = master["PLU코드"].astype(str).str.strip().map(normalize_plu)
    master["상품명"] = master["상품명"].astype(str).str.strip()
    master = master[
        master["PLU코드"].ne("") &
        master["상품명"].ne("") &
        master["PLU코드"].ne("nan") &
        master["상품명"].ne("nan")
    ].copy()

    # 분류 컬럼 채우기
    for col in ("대분류", "중분류", "소분류"):
        if col not in master.columns:
            master[col] = ""
        else:
            master[col] = master[col].fillna("").astype(str).str.strip()

    total_raw = len(master)

    # ── 중복 상품명 처리 ──
    # 같은 상품명에 PLU가 여러 개인 경우: 13자리 우선, 그 중 숫자 큰 것 우선
    master["__norm"] = master["상품명"].map(normalize_name)
    master["__norm_loose"] = master["상품명"].map(normalize_name_loose)
    master["__plu_len"] = master["PLU코드"].str.len()
    master["__plu_num"] = pd.to_numeric(master["PLU코드"], errors="coerce").fillna(0)

    # 13자리 PLU를 가장 우선시 (EAN-13 = 정규 바코드)
    master["__plu_priority"] = master["__plu_len"].apply(lambda x: 0 if x == 13 else 1)

    master = master.sort_values(
        by=["__norm", "__plu_priority", "__plu_num"],
        ascending=[True, True, False],
        na_position="last",
    ).drop_duplicates(subset=["__norm"], keep="first")

    # ── 매칭 테이블 생성 (3가지 키) ──
    lookup: Dict[str, dict] = {}
    lookup_loose: Dict[str, dict] = {}

    for _, row in master.iterrows():
        entry = {
            "plu_code":    row["PLU코드"],
            "product_name": row["상품명"],
            "cat_l": row.get("대분류", ""),
            "cat_m": row.get("중분류", ""),
            "cat_s": row.get("소분류", ""),
        }
        norm_key = row["__norm"]
        loose_key = row["__norm_loose"]

        if norm_key and norm_key not in lookup:
            lookup[norm_key] = entry
        if loose_key and loose_key not in lookup_loose:
            lookup_loose[loose_key] = entry

    deduped = len(master)
    print(f"  ✅ 분류기준표 로드 완료: {total_raw:,}개 → 중복 제거 후 {deduped:,}개 유효 상품")
    print(f"     Exact 매칭 테이블: {len(lookup):,}개 | Loose 매칭 테이블: {len(lookup_loose):,}개")

    # Fuzzy 매칭용 후보 리스트도 반환 (별도 처리)
    master.__fuzzy_lookup = lookup       # 비공개 속성으로 전달용
    master.__fuzzy_lookup_loose = lookup_loose

    return lookup, lookup_loose, master["상품명"].tolist()


def _read_master_file(path: str) -> Optional[pd.DataFrame]:
    """
    분류기준표 파일 1개 읽기.
    헤더 위치 자동 탐지 (PLU코드 글자가 있는 행 찾기).
    """
    ext = Path(path).suffix.lower()
    try:
        # 헤더 탐지를 위해 먼저 10행 probe
        if ext in (".xlsx", ".xls"):
            probe = pd.read_excel(path, header=None, nrows=10, dtype=str)
        else:
            try:
                probe = pd.read_csv(path, header=None, nrows=10, dtype=str, encoding="utf-8-sig")
            except UnicodeDecodeError:
                probe = pd.read_csv(path, header=None, nrows=10, dtype=str, encoding="cp949")

        # 헤더 행 찾기
        header_row = 0
        for i, row in probe.iterrows():
            vals = [str(v) for v in row.values if pd.notna(v)]
            if any("PLU" in v.upper() for v in vals) and any("상품명" in v for v in vals):
                header_row = int(i)
                break

        # 본 데이터 읽기
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(path, header=header_row, dtype=str)
        else:
            try:
                df = pd.read_csv(path, header=header_row, dtype=str, encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(path, header=header_row, dtype=str, encoding="cp949")

        df.columns = [str(c).strip() for c in df.columns]
        return df

    except Exception as e:
        print(f"  ⚠ 파일 읽기 실패 [{Path(path).name}]: {e}")
        return None


# ══════════════════════════════════════════════
# ④ 판매현황 파일 읽기
# ══════════════════════════════════════════════

def load_sales_file(path: str) -> pd.DataFrame:
    """
    이마트24 판매현황 xlsx 파일 1개 읽기.
    반환: [product_name, sales, category_hint] DataFrame
    """
    ext = Path(path).suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            raw = pd.read_excel(path, header=None, dtype=str)
        else:
            try:
                raw = pd.read_csv(path, header=None, dtype=str, encoding="utf-8-sig")
            except UnicodeDecodeError:
                raw = pd.read_csv(path, header=None, dtype=str, encoding="cp949")
    except Exception as e:
        print(f"    ⚠ 파일 읽기 실패 [{Path(path).name}]: {e}")
        return pd.DataFrame()

    # 최소 3컬럼 필요 (col0=상품명, col2=매출합계)
    if raw.shape[1] < 3:
        return pd.DataFrame()

    # row 5~부터 실제 데이터
    data = raw.iloc[5:].reset_index(drop=True).copy()
    if data.empty:
        return pd.DataFrame()

    records = []
    current_category = ""

    for _, row in data.iterrows():
        name_raw = row.iloc[0]
        name = str(name_raw).strip() if pd.notna(name_raw) else ""
        if not name or name.lower() in ("nan", "none"):
            continue

        # 소계행 → 카테고리 힌트 업데이트 후 건너뜀
        if is_subtotal_row(name):
            # 짧고 간단한 이름만 카테고리로 채택 (ex: '음료', '과자')
            if len(name) <= 10 and "(" not in name and ")" not in name:
                current_category = name
            continue

        # sales 파싱 (col 2 = 매출합계)
        raw_sales = row.iloc[2] if pd.notna(row.iloc[2]) else "0"
        try:
            sales_val = int(float(str(raw_sales).replace(",", "").strip()))
        except (ValueError, TypeError):
            sales_val = 0

        records.append({
            "product_name":    name,
            "sales":           sales_val,
            "category_hint":   current_category,
        })

    return pd.DataFrame(records) if records else pd.DataFrame()


def collect_all_sales(input_dirs: List[str]) -> pd.DataFrame:
    """
    여러 입력 디렉토리에서 전체 판매 데이터 수집.
    날짜별 하위 폴더 구조 자동 탐지.
    """
    all_frames = []
    processed_dates = set()

    for input_dir in input_dirs:
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"  ⚠ 경로 없음: {input_dir}")
            continue

        subdirs = sorted([d for d in input_path.iterdir() if d.is_dir()])

        if subdirs:
            # 날짜별 하위 폴더 구조
            for subdir in subdirs:
                folder_date = parse_date_from_foldername(subdir.name)
                if folder_date is None:
                    continue

                xlsx_files = sorted(subdir.glob("*.xlsx")) + sorted(subdir.glob("*.xls"))
                if not xlsx_files:
                    continue

                day_frames = []
                for fpath in xlsx_files:
                    df = load_sales_file(str(fpath))
                    if not df.empty:
                        day_frames.append(df)

                if day_frames:
                    day_df = pd.concat(day_frames, ignore_index=True)
                    day_df["date"] = pd.Timestamp(folder_date)
                    all_frames.append(day_df)
                    processed_dates.add(folder_date)
        else:
            # 파일 직접 포함 구조
            xlsx_files = sorted(input_path.glob("*.xlsx")) + sorted(input_path.glob("*.xls"))
            for fpath in xlsx_files:
                file_date = parse_date_from_filename(str(fpath))
                if file_date is None:
                    continue
                df = load_sales_file(str(fpath))
                if not df.empty:
                    df["date"] = pd.Timestamp(file_date)
                    all_frames.append(df)
                    processed_dates.add(file_date)

    if not all_frames:
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)
    date_range = f"{min(processed_dates)} ~ {max(processed_dates)}" if processed_dates else "?"
    print(f"  ✅ 전체 수집: {len(combined):,}행 | {len(processed_dates)}일 ({date_range})")
    return combined


# ══════════════════════════════════════════════
# ⑤ PLU 매칭 (3단계 전략)
# ══════════════════════════════════════════════

def match_plu(
    sales_df: pd.DataFrame,
    lookup: Dict[str, dict],
    lookup_loose: Dict[str, dict],
    all_master_names: List[str],
    fuzzy_threshold: float = 0.82,
) -> pd.DataFrame:
    """
    판매현황 상품명 → PLU 매칭 (3단계).

    1단계: 정규화 Exact  (normalize_name)
    2단계: Loose Exact   (normalize_name_loose, 특수문자 제거)
    3단계: Fuzzy         (difflib, threshold=0.82 보수적 적용)
    미매칭: plu_code='' 기록

    반환 컬럼 추가:
      plu_code, cat_l, cat_m, cat_s, match_type
    """
    # Fuzzy용 정규화된 후보 목록 (사전 계산)
    norm_cands = {normalize_name(n): n for n in all_master_names if n}
    norm_cand_keys = list(norm_cands.keys())

    results = []
    stats = {"exact": 0, "loose": 0, "fuzzy": 0, "unmatched": 0}
    fuzzy_log = []
    unmatched_log = []

    for _, row in sales_df.iterrows():
        name = str(row["product_name"]).strip()

        # ── 1단계: Exact 매칭 ──
        norm = normalize_name(name)
        if norm in lookup:
            m = lookup[norm]
            results.append({**row.to_dict(), **m, "match_type": "exact"})
            stats["exact"] += 1
            continue

        # ── 2단계: Loose Exact 매칭 (특수문자 무시) ──
        loose = normalize_name_loose(name)
        if loose in lookup_loose:
            m = lookup_loose[loose]
            results.append({**row.to_dict(), **m, "match_type": "loose_exact"})
            stats["loose"] += 1
            continue

        # ── 3단계: Fuzzy 매칭 (보수적) ──
        fuzzy_result = _fuzzy_match(norm, norm_cand_keys, threshold=fuzzy_threshold)
        if fuzzy_result:
            matched_norm, score = fuzzy_result
            original_name = norm_cands[matched_norm]
            orig_norm = normalize_name(original_name)
            m = lookup.get(orig_norm) or lookup_loose.get(normalize_name_loose(original_name), {})
            if m:
                results.append({**row.to_dict(), **m, "match_type": f"fuzzy({score:.2f})"})
                stats["fuzzy"] += 1
                fuzzy_log.append((name, original_name, f"{score:.2f}"))
                continue

        # ── 미매칭 ──
        results.append({
            **row.to_dict(),
            "plu_code": "",
            "cat_l": row.get("category_hint", "기타"),
            "cat_m": row.get("category_hint", "기타"),
            "cat_s": "",
            "match_type": "unmatched",
        })
        stats["unmatched"] += 1
        unmatched_log.append(name)

    result_df = pd.DataFrame(results)
    total = len(result_df)

    # 매칭 결과 요약
    print(f"\n  ┌─ PLU 매칭 결과 {'─'*30}")
    print(f"  │  전체  : {total:>5}개  (100.0%)")
    print(f"  │  Exact : {stats['exact']:>5}개  ({stats['exact']/total*100:.1f}%)")
    print(f"  │  Loose : {stats['loose']:>5}개  ({stats['loose']/total*100:.1f}%)")
    print(f"  │  Fuzzy : {stats['fuzzy']:>5}개  ({stats['fuzzy']/total*100:.1f}%)")
    print(f"  │  미매칭: {stats['unmatched']:>5}개  ({stats['unmatched']/total*100:.1f}%)  ← 분류기준표에 없는 신상품")
    print(f"  └─ 전체 매칭률: {(total-stats['unmatched'])/total*100:.1f}%")

    if fuzzy_log:
        print(f"\n  ⚠ Fuzzy 매칭 목록 (확인 권장):")
        for orig, cand, sc in fuzzy_log[:20]:
            print(f"    '{orig}' → '{cand}'  (유사도: {sc})")
        if len(fuzzy_log) > 20:
            print(f"    ... 외 {len(fuzzy_log)-20}건")

    if unmatched_log:
        print(f"\n  ℹ 미매칭 목록 ({len(unmatched_log)}건) → unmatched 리포트 파일에 저장됨")
        for name in unmatched_log[:10]:
            print(f"    - {name}")
        if len(unmatched_log) > 10:
            print(f"    ... 외 {len(unmatched_log)-10}건")

    # 미매칭 리스트 result_df에 별도 저장 (나중에 파일 저장용)
    result_df.attrs["unmatched_names"] = unmatched_log
    result_df.attrs["fuzzy_names"] = fuzzy_log

    return result_df


def _fuzzy_match(
    query: str,
    candidates: List[str],
    threshold: float,
) -> Optional[Tuple[str, float]]:
    """
    Fuzzy 매칭 내부 함수.
    1. get_close_matches로 빠른 후보 탐색
    2. SequenceMatcher로 정밀 점수 계산
    """
    if not query:
        return None

    # 1차: get_close_matches (빠름)
    hits = get_close_matches(query, candidates, n=3, cutoff=threshold)
    if hits:
        best = max(hits, key=lambda h: SequenceMatcher(None, query, h).ratio())
        score = SequenceMatcher(None, query, best).ratio()
        if score >= threshold:
            return best, score

    # 2차: 길이 필터 후 전체 순회 (get_close_matches 놓친 경우 보완)
    # 길이 차이가 너무 크면 제외 (최대 30% 차이)
    q_len = len(query)
    filtered = [c for c in candidates if abs(len(c) - q_len) <= q_len * 0.3 + 3]
    if not filtered:
        return None

    best_score, best_cand = 0.0, None
    for cand in filtered:
        score = SequenceMatcher(None, query, cand).ratio()
        if score > best_score:
            best_score, best_cand = score, cand

    if best_score >= threshold:
        return best_cand, best_score

    return None


# ══════════════════════════════════════════════
# ⑥ 피처 생성 (lag/rolling/캘린더/안전재고)
# ══════════════════════════════════════════════

def build_lag_rolling(df: pd.DataFrame) -> pd.DataFrame:
    """
    plu_code(또는 product_name)별 lag/rolling 피처 계산.

    Data Leakage 방지 원칙:
      shift(1) 먼저 적용 후 rolling 계산
      → 오늘 데이터로 오늘을 예측하는 오류 방지

    피처:
      lag_1         : 어제 판매량
      lag_3         : 3일 전 판매량
      lag_7         : 7일 전 판매량 (동일 요일)
      rolling_7_mean: 최근 7일 평균 (어제 기준)
      rolling_7_std : 최근 7일 표준편차 (판매 변동성)
    """
    # 키 컬럼: PLU 있으면 PLU, 없으면 product_name
    key_col = "plu_code" if (
        "plu_code" in df.columns and
        df["plu_code"].ne("").any() and
        df["plu_code"].notna().any()
    ) else "product_name"

    df["date"] = pd.to_datetime(df["date"])
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)

    result_frames = []

    for key_val, group in df.groupby(key_col, dropna=False):
        # 동일 날짜 중복 합산 (여러 카테고리 파일에서 같은 상품이 나올 수 있음)
        daily = (
            group.groupby("date")["sales"]
            .sum()
            .reset_index()
            .sort_values("date")
        )

        # 전체 기간 일 단위 재색인 (빈 날짜 = 판매량 0)
        full_idx = pd.date_range(
            start=daily["date"].min(),
            end=daily["date"].max(),
            freq="D"
        )
        series = (
            daily.set_index("date")["sales"]
            .reindex(full_idx, fill_value=0.0)
            .astype(float)
        )

        # shift(1) 적용 후 rolling → leakage 방지
        shifted = series.shift(1)

        lag_frame = pd.DataFrame({
            "date":           full_idx,
            key_col:          key_val,
            "lag_1":          shifted.values,
            "lag_3":          series.shift(3).values,
            "lag_7":          series.shift(7).values,
            "rolling_7_mean": shifted.rolling(window=7, min_periods=1).mean().values,
            "rolling_7_std":  shifted.rolling(window=7, min_periods=1).std(ddof=0).values,
        })
        result_frames.append(lag_frame)

    if not result_frames:
        return df

    lag_df = pd.concat(result_frames, ignore_index=True)
    merged = df.merge(lag_df, on=["date", key_col], how="left")

    for col in ("lag_1", "lag_3", "lag_7", "rolling_7_mean", "rolling_7_std"):
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)

    # merge 이후 plu_code가 NaN으로 바뀌는 것 방지
    if "plu_code" in merged.columns:
        merged["plu_code"] = merged["plu_code"].fillna("").astype(str).str.strip().replace("nan", "")

    return merged


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    캘린더 피처 추가.
    day_of_week : 월=0, 화=1, ..., 일=6
    month       : 1~12
    is_holiday  : 공휴일 OR 주말 = 1
    academic_event     : 0 (Phase 0 기본값, 추후 학사일정 JSON으로 채움)
    building_headcount : 0 (Phase 0 기본값, 추후 시간표 CSV로 채움)
    """
    dt = pd.to_datetime(df["date"])
    df["day_of_week"] = dt.dt.weekday.astype(int)
    df["month"] = dt.dt.month.astype(int)

    years = dt.dt.year.dropna().unique().astype(int).tolist()
    holiday_set = get_holiday_set(years)
    is_holiday = dt.dt.normalize().isin(holiday_set)
    is_weekend = dt.dt.dayofweek >= 5
    df["is_holiday"] = (is_holiday | is_weekend).astype(int)

    # Phase 0 기본값
    df["academic_event"] = 0
    df["building_headcount"] = 0

    return df


def add_safety_stock(df: pd.DataFrame) -> pd.DataFrame:
    """
    안전재고 = rolling_7_mean × 카테고리 배율
    우선순위: cat_m(중분류) > cat_l(대분류) > category_hint
    """
    def get_category(row):
        for col in ("cat_m", "cat_l", "category_hint"):
            v = str(row.get(col, "")).strip()
            if v and v not in ("", "기타", "nan"):
                return v
        return "기타"

    categories = df.apply(get_category, axis=1)
    multipliers = categories.map(safety_stock_multiplier)
    df["safety_stock"] = (
        df["rolling_7_mean"] * multipliers
    ).round().clip(lower=0).fillna(0).astype(int)
    return df


# ══════════════════════════════════════════════
# ⑦ 출력 정리 및 저장
# ══════════════════════════════════════════════

def finalize_output(df: pd.DataFrame) -> pd.DataFrame:
    """
    컬럼 타입 정리 및 출력 순서 정렬.
    """
    # plu_code 컬럼 통일 (NaN → 빈 문자열)
    if "plu_code" not in df.columns:
        df["plu_code"] = ""
    df["plu_code"] = df["plu_code"].fillna("").astype(str).str.strip().replace("nan", "")

    # cat 컬럼 통일
    for col, src in [("category_l", "cat_l"), ("category_m", "cat_m"), ("category_s", "cat_s")]:
        if col not in df.columns:
            df[col] = df.get(src, "")
        df[col] = df[col].fillna("").astype(str).str.strip().replace("nan", "")

    # 빈 category는 category_hint로 채움
    for col in ("category_l", "category_m"):
        mask = df[col].eq("")
        df.loc[mask, col] = df.loc[mask, "category_hint"].fillna("기타")
    df["category_s"] = df["category_s"].replace("", "")

    # 수치형 정리
    df["sales"]    = df["sales"].fillna(0).astype(int)
    df["lag_1"]    = df["lag_1"].round().astype(int)
    df["lag_3"]    = df["lag_3"].round().astype(int)
    df["lag_7"]    = df["lag_7"].round().astype(int)
    df["rolling_7_mean"] = df["rolling_7_mean"].round(2)
    df["rolling_7_std"]  = df["rolling_7_std"].round(2)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # 출력 컬럼 선택 및 정렬
    final_cols = [c for c in OUTPUT_COLS if c in df.columns]
    return df[final_cols].copy()


def save_outputs(
    feature_df: pd.DataFrame,
    output_dir: str,
    unmatched_names: List[str],
    fuzzy_names: List[Tuple],
) -> Tuple[Path, Path]:
    """CSV + XLSX + 미매칭 리포트 저장."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 날짜 범위 레이블
    dates = sorted(feature_df["date"].unique())
    if dates:
        start = dates[0].replace("-", "_")
        end   = dates[-1].replace("-", "_")
        label = f"{start}_to_{end}" if start != end else start
    else:
        label = datetime.today().strftime("%Y_%m_%d")

    csv_path  = out_path / f"sales_{label}_features.csv"
    xlsx_path = out_path / f"sales_{label}_features.xlsx"

    # plu_code 빈 문자열(미매칭) 보존: dtype={'plu_code': str} 로 읽어야 빈 칸 유지
    feature_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    feature_df.to_excel(xlsx_path, index=False)

    # 미매칭 리포트 저장
    if unmatched_names:
        report_path = out_path / f"sales_{label}_unmatched.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# 미매칭 상품 목록 ({len(unmatched_names)}건)\n")
            f.write("# 분류기준표에 없는 신상품이거나 상품명 표기가 다른 경우\n")
            f.write("# 해결방법: 분류기준표에 추가하거나 상품명 수정 후 재실행\n\n")
            for name in sorted(set(unmatched_names)):
                f.write(f"{name}\n")
        print(f"  📄 미매칭 리포트: {report_path}")

    # Fuzzy 매칭 리포트 저장
    if fuzzy_names:
        fuzzy_path = out_path / f"sales_{label}_fuzzy_check.txt"
        with open(fuzzy_path, "w", encoding="utf-8") as f:
            f.write(f"# Fuzzy 매칭 목록 ({len(fuzzy_names)}건)\n")
            f.write("# 자동 매칭되었지만 수동 확인이 필요한 항목\n")
            f.write("# 형식: [판매현황 상품명] → [분류기준표 상품명] (유사도)\n\n")
            for orig, cand, sc in fuzzy_names:
                f.write(f"'{orig}' → '{cand}'  (유사도: {sc})\n")
        print(f"  📄 Fuzzy 확인 리포트: {fuzzy_path}")

    n_products = feature_df["product_name"].nunique() if "product_name" in feature_df.columns else "?"
    n_days = feature_df["date"].nunique()
    print(f"\n  💾 CSV  저장: {csv_path}")
    print(f"  💾 XLSX 저장: {xlsx_path}")
    print(f"     총 {len(feature_df):,}행 | {n_days}일 | {n_products}개 상품")

    return csv_path, xlsx_path


# ══════════════════════════════════════════════
# ⑧ 메인 파이프라인
# ══════════════════════════════════════════════

def run(
    input_dir: str,
    master_dir: str,
    output_dir: str = "data/processed",
    fuzzy_threshold: float = 0.82,
) -> Optional[Tuple[Path, Path]]:
    """
    메인 실행 함수 (터미널 / Colab 공용).

    Parameters
    ----------
    input_dir       : 판매현황 파일 루트 디렉토리 (콤마로 여러 개 가능)
    master_dir      : 분류기준표 폴더 또는 단일 파일 경로
    output_dir      : 결과 저장 폴더
    fuzzy_threshold : Fuzzy 매칭 임계값 (기본 0.82, 높을수록 보수적)
    """
    print("=" * 62)
    print("  에러없조 | 판매현황 → RF 학습 데이터 변환기 v2")
    print("=" * 62)

    # 입력 경로 파싱 (콤마 구분 다중 경로 지원)
    input_dirs = [p.strip() for p in str(input_dir).split(",") if p.strip()]
    print(f"  입력 : {', '.join(input_dirs)}")
    print(f"  분류기준표 : {master_dir}")
    print(f"  출력 : {output_dir}")
    print(f"  Fuzzy 임계값 : {fuzzy_threshold}")

    # ── Step 1: 분류기준표 로드 ──
    print(f"\n[Step 1] 분류기준표 로드")
    try:
        lookup, lookup_loose, all_master_names = load_master(master_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"  ❌ {e}")
        return None

    # ── Step 2: 판매 데이터 수집 ──
    print(f"\n[Step 2] 판매 데이터 수집")
    raw_df = collect_all_sales(input_dirs)
    if raw_df.empty:
        print("  ❌ 수집된 데이터가 없습니다.")
        return None

    # ── Step 3: PLU 매칭 ──
    print(f"\n[Step 3] PLU 매칭")
    matched_df = match_plu(raw_df, lookup, lookup_loose, all_master_names, fuzzy_threshold)
    unmatched_names = matched_df.attrs.get("unmatched_names", [])
    fuzzy_names     = matched_df.attrs.get("fuzzy_names", [])

    # ── Step 4: 중복 집계 (날짜 × PLU 단위) ──
    print(f"\n[Step 4] 중복 집계")
    matched_df["date"]  = pd.to_datetime(matched_df["date"])
    matched_df["sales"] = pd.to_numeric(matched_df["sales"], errors="coerce").fillna(0)

    # 집계 키: PLU 있으면 PLU, 없으면 product_name
    has_plu = matched_df["plu_code"].ne("").any() if "plu_code" in matched_df.columns else False
    group_keys = (
        ["date", "plu_code", "product_name", "cat_l", "cat_m", "cat_s", "match_type", "category_hint"]
        if has_plu else
        ["date", "product_name", "cat_l", "cat_m", "cat_s", "match_type", "category_hint"]
    )
    group_keys = [k for k in group_keys if k in matched_df.columns]

    agg_df = matched_df.groupby(group_keys, as_index=False)["sales"].sum()

    if not has_plu:
        agg_df["plu_code"] = ""

    # 집계 후에도 plu_code NaN 방지
    if "plu_code" in agg_df.columns:
        agg_df["plu_code"] = agg_df["plu_code"].fillna("").astype(str).str.strip().replace("nan", "")

    print(f"  집계 후: {len(agg_df):,}행 (날짜×상품 단위)")

    # ── Step 5: lag/rolling 피처 ──
    print(f"\n[Step 5] Lag/Rolling 피처 생성")
    feature_df = build_lag_rolling(agg_df)
    print(f"  완료: {len(feature_df):,}행")

    # ── Step 6: 캘린더 + 안전재고 ──
    print(f"\n[Step 6] 캘린더 피처 + 안전재고")
    feature_df = add_calendar_features(feature_df)
    feature_df = add_safety_stock(feature_df)

    # ── Step 7: 출력 정리 ──
    print(f"\n[Step 7] 출력 정리")
    feature_df = finalize_output(feature_df)

    # ── Step 8: 저장 ──
    print(f"\n[Step 8] 저장")
    return save_outputs(feature_df, output_dir, unmatched_names, fuzzy_names)


# ══════════════════════════════════════════════
# ⑨ CLI 진입점
# ══════════════════════════════════════════════

def _is_interactive() -> bool:
    try:
        shell = get_ipython().__class__.__name__  # type: ignore  # noqa
        return "ZMQ" in shell or "Colab" in shell or "Terminal" not in shell
    except NameError:
        return False


def main():
    if _is_interactive():
        print("=" * 55)
        print("Colab / Jupyter 환경입니다. run() 함수를 사용하세요.")
        print()
        print("from converter_v2 import run")
        print("run(")
        print("    input_dir='data/raw/240501-15',")
        print("    master_dir='csv_상품분류기준표',")
        print("    output_dir='data/processed'")
        print(")")
        print("=" * 55)
        return

    parser = argparse.ArgumentParser(
        description="이마트24 판매현황 xlsx → RF 학습용 feature CSV 변환기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 실행
  python converter_v2.py --input data/raw/240501-15 --master csv_상품분류기준표

  # 여러 폴더 동시 처리
  python converter_v2.py --input "data/raw/240501-15,data/raw/240601-30" --master csv_상품분류기준표

  # 출력 폴더 지정
  python converter_v2.py --input data/raw/240501-15 --master csv_상품분류기준표 --output data/processed

  # Fuzzy 임계값 조정 (낮출수록 더 많이 매칭, 높을수록 더 보수적)
  python converter_v2.py --input data/raw/240501-15 --master csv_상품분류기준표 --fuzzy-threshold 0.85
        """
    )
    parser.add_argument("--input",  required=True,
                        help="판매현황 루트 디렉토리 (콤마로 여러 개 가능)")
    parser.add_argument("--master", required=True,
                        help="분류기준표 폴더 또는 단일 CSV/xlsx 경로")
    parser.add_argument("--output", default="data/processed",
                        help="결과 저장 폴더 (기본: data/processed)")
    parser.add_argument("--fuzzy-threshold", type=float, default=0.82,
                        help="Fuzzy 매칭 임계값 (기본: 0.82)")
    args = parser.parse_args()

    run(
        input_dir=args.input,
        master_dir=args.master,
        output_dir=args.output,
        fuzzy_threshold=args.fuzzy_threshold,
    )


if __name__ == "__main__":
    main()
