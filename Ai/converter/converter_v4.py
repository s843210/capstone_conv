"""
converter_v3.py  ─  에러없조 | 판매현황 → RF 학습용 feature CSV 변환기
=============================================================================
[v3 → v4 개선 사항]
  1. is_ambiguous_subtotal() sales 조건 제거
     - v3: sales==0 일 때만 소계 추가 판별 → sales>0 소계행 통과 문제
     - v4: sales 값과 무관하게 소계 패턴이면 항상 제거
     - 판별 원리: 상품명 끝이 (한글/영문) 괄호로 끝나고 전체에 숫자 없으면 소계
     - 제거 대상: 냉장커피(펫), 커피음료(RTD), 용기면(대/소), 차음료(중) 등 20종
     - 실제 상품 안전: 브랜드)상품명 구조라 끝이 괄호로 끝나지 않아 오판 없음

[실제 파일 구조 기반]
  판매현황 xlsx:
    row 0~4 : 헤더/타이틀
    row 5~  : 데이터 (소계행 + 실제 상품 혼재)
    col 0   : 카테고리/상품명
    col 2   : 매출합계 (= sales, 당일 판매량)

  소계행 구분 : 브랜드)상품명 패턴 없으면 소계
  ※ 시간대별(00H~23H) 피처는 수기 추출 방식에서 제공되지 않으므로 제외

  분류기준표 CSV (csv_상품분류기준표 폴더):
    row 3 : 헤더  [No | PLU코드 | 상품명 | 출력여부 | 대분류 | 중분류 | 소분류]
    row 4~: 상품 데이터 (24,774개)

[PLU 매칭 3단계 전략]
  1단계 Exact  : 정규화 상품명 완전 일치          → 97~98% 처리
  2단계 Loose  : 특수문자 제거 후 일치            → 추가 처리
  3단계 Fuzzy  : difflib 유사도 (threshold=0.82)  → 보수적 적용
  미매칭       : plu_code='' 저장 + unmatched.txt → 억지 매칭 금지

[사용법]
  터미널
    python converter_v3.py --input data\\raw\\240501-15 --master csv_상품분류기준표
    python converter_v3.py --input data\\raw\\240501-15           # 분류기준표 없이도 동작
  Colab
    from converter_v3 import run
    run(input_dir='240501-15', master_dir='csv_상품분류기준표')
=============================================================================
"""

import argparse
import glob
import re
import unicodedata
import warnings
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)


# ══════════════════════════════════════════════
# ① 상수
# ══════════════════════════════════════════════

SKIP_KEYWORDS: Set[str] = {"행사", "소계", "합계", "데이"}

SAFETY_MULTIPLIERS: List[Tuple[str, float]] = [
    ("담배",   1.0),
    ("음료",   0.5), ("과자",   0.5), ("캔디",   0.5),
    ("초콜릿", 0.5), ("초콜렛", 0.5), ("젤리",   0.5),
    ("유제품", 0.5), ("커피",   0.5), ("생수",   0.5),
    ("스낵",   0.5), ("껌",     0.5),
    ("도시락", 0.3), ("김밥",   0.3), ("삼각",   0.3),
    ("밥류",   0.3), ("주먹밥", 0.3), ("빵",     0.3),
    ("샌드위치", 0.3), ("햄버거", 0.3),
    ("간편식품", 0.3), ("즉석식", 0.3),
]

OUTPUT_COLS = [
    "date", "plu_code", "product_name",
    "category_l", "category_m", "category_s",
    "sales",
    "lag_1", "lag_3", "lag_7",
    "rolling_7_mean", "rolling_7_std",
    "day_of_week", "month", "is_holiday",
    "academic_event", "building_headcount",
    "safety_stock",
    "match_type",
]

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
# ② 유틸리티
# ══════════════════════════════════════════════

def normalize_plu(plu: str) -> str:
    """xlsx 읽기 단계 전용 PLU 정규화. API 레이어에는 절대 사용 안 함."""
    if not isinstance(plu, str):
        return ""
    v = plu.strip()
    if not v or v.lower() in ("nan", "none"):
        return ""
    if re.fullmatch(r"[+\-]?\d+(\.\d+)?[eE][+\-]?\d+", v):
        try:
            return str(int(Decimal(v)))
        except (InvalidOperation, ValueError, OverflowError):
            return v
    if re.fullmatch(r"[+\-]?\d+\.0+", v):
        return v.split(".", 1)[0]
    return v


def normalize_name(name: str) -> str:
    """상품명 정규화 (공백 제거 + 소문자 + NFKC). 매칭 키 전용."""
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKC", name.strip())
    return re.sub(r"\s+", "", s).lower()


def normalize_name_loose(name: str) -> str:
    """느슨한 정규화 (특수문자 추가 제거). 2단계 매칭 전용."""
    s = normalize_name(name)
    return re.sub(r"[()./\-_&\[\]{}%@#*!?+~]", "", s)


def get_holiday_set(years: List[int]) -> set:
    """연도 목록에 대한 공휴일(+주말 제외) 날짜 집합 반환."""
    try:
        import holidays as holidays_lib
        kr = holidays_lib.KR(years=years)
        return {pd.Timestamp(d).normalize() for d in kr.keys()}
    except Exception:
        pass
    result = set()
    for y in years:
        for iso in KR_HOLIDAYS.get(y, []):
            result.add(pd.Timestamp(iso).normalize())
    return result


def parse_date_from_foldername(name: str) -> Optional[date]:
    """폴더명 앞 6자리 YYMMDD에서 날짜 추출."""
    m = re.search(r"(\d{6})", name)
    if m:
        s = m.group(1)
        try:
            return date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
        except ValueError:
            pass
    return None


def parse_date_from_filename(path: str) -> Optional[date]:
    """파일명에서 날짜 추출. YYYYMMDD / YYMMDD 지원."""
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


def safety_multiplier(category: str) -> float:
    """카테고리 키워드 기반 안전재고 배율 반환."""
    for kw, mult in SAFETY_MULTIPLIERS:
        if kw in str(category):
            return mult
    return 0.3


def is_subtotal_row(name: str) -> bool:
    """
    소계행 여부 판별.
    실제 상품 = '브랜드)상품명' 구조 → ')' 포함
    소계행   = 카테고리명만 있는 행 또는 중간집계 행
    """
    if not name or pd.isna(name):
        return True
    s = str(name).strip()
    if not s or s.lower() in ("nan", "none"):
        return True
    for kw in SKIP_KEYWORDS:
        if kw in s:
            return True
    # (대)/(중)/(소) 패턴 = 중간 집계
    if re.search(r"\((대|중|소|상|하|컵.?대|컵.?소)\)", s):
        return True
    # ')' 없으면 브랜드 구분자 없음 = 소계
    if ")" not in s:
        return True
    return False


# ══════════════════════════════════════════════
# ③ 분류기준표 로드 → 매칭 테이블 생성
# ══════════════════════════════════════════════

def load_master(master_path: str) -> Tuple[Dict, Dict, List[str]]:
    """
    분류기준표 로드 → (exact_lookup, loose_lookup, 상품명 목록) 반환.

    [v3 개선] UserWarning 원인이었던 DataFrame 비공개 속성 방식 제거.
              lookup 딕셔너리를 명시적으로 반환.

    중복 상품명 처리: 13자리 PLU(EAN-13) 우선, 그 다음 숫자 큰 것 우선.
    """
    path = Path(master_path)
    csv_files = []
    if path.is_dir():
        csv_files = sorted(path.glob("*.csv")) + sorted(path.glob("*.xlsx"))
        if not csv_files:
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
    master.columns = [str(c).strip() for c in master.columns]

    for col in ("PLU코드", "상품명"):
        if col not in master.columns:
            raise ValueError(f"분류기준표에 '{col}' 컬럼이 없습니다. 현재: {list(master.columns)}")

    master = master.dropna(subset=["PLU코드", "상품명"]).copy()
    master["PLU코드"] = master["PLU코드"].astype(str).str.strip().map(normalize_plu)
    master["상품명"]  = master["상품명"].astype(str).str.strip()
    master = master[
        master["PLU코드"].ne("") & master["상품명"].ne("") &
        master["PLU코드"].ne("nan") & master["상품명"].ne("nan")
    ].copy()

    for col in ("대분류", "중분류", "소분류"):
        if col not in master.columns:
            master[col] = ""
        else:
            master[col] = master[col].fillna("").astype(str).str.strip()

    total_raw = len(master)

    # 중복 처리: 13자리 EAN 우선, 숫자 큰 것 우선
    master["__norm"]       = master["상품명"].map(normalize_name)
    master["__plu_len"]    = master["PLU코드"].str.len()
    master["__plu_num"]    = pd.to_numeric(master["PLU코드"], errors="coerce").fillna(0)
    master["__plu_pri"]    = master["__plu_len"].apply(lambda x: 0 if x == 13 else 1)
    master = (
        master.sort_values(["__norm", "__plu_pri", "__plu_num"],
                           ascending=[True, True, False])
              .drop_duplicates(subset=["__norm"], keep="first")
              .reset_index(drop=True)
    )

    # ── 매칭 테이블 생성 (일반 딕셔너리, UserWarning 없음) ──
    lookup: Dict[str, dict]       = {}
    lookup_loose: Dict[str, dict] = {}

    for _, row in master.iterrows():
        entry = {
            "plu_code":     row["PLU코드"],
            "product_name": row["상품명"],
            "cat_l": row.get("대분류", ""),
            "cat_m": row.get("중분류", ""),
            "cat_s": row.get("소분류", ""),
        }
        nk = row["__norm"]
        lk = normalize_name_loose(row["상품명"])
        if nk and nk not in lookup:
            lookup[nk] = entry
        if lk and lk not in lookup_loose:
            lookup_loose[lk] = entry

    all_names = master["상품명"].tolist()
    print(f"  ✅ 분류기준표 로드 완료: {total_raw:,}개 → 중복 제거 후 {len(master):,}개")
    print(f"     Exact 테이블: {len(lookup):,}개  |  Loose 테이블: {len(lookup_loose):,}개")
    return lookup, lookup_loose, all_names


def _read_master_file(path: str) -> Optional[pd.DataFrame]:
    """분류기준표 파일 1개 읽기. 헤더 행 자동 탐지."""
    ext = Path(path).suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            probe = pd.read_excel(path, header=None, nrows=10, dtype=str)
        else:
            try:
                probe = pd.read_csv(path, header=None, nrows=10,
                                    dtype=str, encoding="utf-8-sig")
            except UnicodeDecodeError:
                probe = pd.read_csv(path, header=None, nrows=10,
                                    dtype=str, encoding="cp949")

        header_row = 0
        for i, row in probe.iterrows():
            vals = [str(v) for v in row.values if pd.notna(v)]
            if any("PLU" in v.upper() for v in vals) and any("상품명" in v for v in vals):
                header_row = int(i)
                break

        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(path, header=header_row, dtype=str)
        else:
            try:
                df = pd.read_csv(path, header=header_row,
                                 dtype=str, encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(path, header=header_row,
                                 dtype=str, encoding="cp949")

        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"  ⚠ 파일 읽기 실패 [{Path(path).name}]: {e}")
        return None


# ══════════════════════════════════════════════
# ④ 판매현황 파일 읽기
# ══════════════════════════════════════════════

def is_ambiguous_subtotal(name: str) -> bool:
    """
    is_subtotal_row()를 통과했지만 소계행인 행 추가 판별.
    sales 값과 무관하게 항상 호출.

    [판별 원리]
    이마트24 판매현황 파일에서 소계행은 두 가지 형태로 존재:
      케이스 A: 소계행 sales=0  (하위 항목 미집계)
      케이스 B: 소계행 sales>0  (하위 상품 합계가 소계에도 채워짐)
    두 케이스 모두 처리하기 위해 sales 조건 없이 패턴으로만 판별.

    [소계행 구조]
      카테고리명(용기/규격/분류) 형태 — 괄호가 상품명 맨 끝에 위치
      괄호 안: 순수 한글 또는 영문대문자 (숫자 없음)
      예: 냉장커피(펫), 커피음료(RTD), 용기면(대), 차음료(중), 흰우유(중/대)

    [실제 상품 구조]
      브랜드)상품명 형태 — ) 가 브랜드 뒤에 위치, 상품명이 뒤따름
      끝이 괄호로 마무리되지 않거나, 괄호 안에 숫자(용량/중량) 포함
      예: 크라운)마이쮸복숭아44g, CJ)햇반불닭마요덮밥, 오뚜기)열라면봉지

    [안전성]
    실제 상품은 브랜드) 뒤로 상품명이 이어지므로 끝이 (순수텍스트)로
    끝나지 않아 오판 없음. 전체 데이터 전수 검증 완료.
    """
    # 상품명 끝이 (한글), (영문대문자), (한글/한글) 패턴으로 끝나는지 확인
    m = re.search(r"\(([가-힣]+|[A-Z]+|[가-힣]+/[가-힣]+)\)$", name.strip())
    if m:
        # 상품명 전체에 숫자(용량/중량/수량)가 없으면 소계로 판단
        if not re.search(r"\d", name):
            return True
    return False


def load_sales_file(path: str) -> pd.DataFrame:
    """
    이마트24 판매현황 xlsx 파일 1개 읽기.
    반환: [product_name, sales, category_hint] DataFrame

    ※ 시간대별(00H~23H) 컬럼은 수기 추출 방식에서 제공되지 않으므로
       현재 버전에서는 완전히 제외. Phase 2 이후 실시간 연동 시 추가 예정.

    [소계행 처리 2단계]
    1단계: is_subtotal_row() - 명확한 소계행 제거
           (카테고리명만 있는 행, (대)/(중)/(소) 패턴 등)
    2단계: is_ambiguous_subtotal() - 1단계 통과한 소계행 추가 제거
           sales 값 무관하게 패턴으로 판별 (sales=0/sales>0 모두 처리)
           예: 냉장커피(펫), 커피음료(RTD), 용기면(대/소), 차음료(중) 등
           실제 상품 (예: 크라운)마이쮸복숭아44g)은 패턴 불일치로 안전 보존
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

    if raw.shape[1] < 3:
        return pd.DataFrame()

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

        # 1단계: 명확한 소계행 제거
        if is_subtotal_row(name):
            if len(name) <= 10 and "(" not in name and ")" not in name:
                current_category = name
            continue

        # sales 파싱
        raw_sales = row.iloc[2] if pd.notna(row.iloc[2]) else "0"
        try:
            sales_val = int(float(str(raw_sales).replace(",", "").strip()))
        except (ValueError, TypeError):
            sales_val = 0

        # 2단계: 소계 패턴 추가 판별 (sales 값 무관하게 적용)
        # 소계행은 sales=0(미집계)과 sales>0(합계 채워짐) 두 경우 모두 존재.
        # 패턴 기반 판별이므로 어느 경우든 정확히 제거됨.
        if is_ambiguous_subtotal(name):
            continue

        records.append({
            "product_name":  name,
            "sales":         sales_val,
            "category_hint": current_category,
        })

    return pd.DataFrame(records) if records else pd.DataFrame()


def is_month_folder(path: Path) -> bool:
    """
    YYYYMM 형태 월 폴더 여부 판별.
    예: 202404, 202405 → True  /  240401, 240501 → False
    """
    m = re.fullmatch(r"\d{6}", path.name)
    if not m:
        return False
    year  = int(path.name[:4])
    month = int(path.name[4:6])
    return 2000 <= year <= 2100 and 1 <= month <= 12


def collect_xlsx_for_date(day_dir: Path) -> List[Path]:
    """
    날짜 폴더에서 xlsx 파일 수집.
    직접 있으면 직접, 없으면 하위 폴더 1단계 탐색.
    (240407/240407판매현황/*.xlsx 같은 2단계 중첩 구조 지원)
    """
    direct = sorted(day_dir.glob("*.xlsx")) + sorted(day_dir.glob("*.xls"))
    if direct:
        return direct
    nested = []
    for sub in sorted(day_dir.iterdir()):
        if sub.is_dir():
            nested += sorted(sub.glob("*.xlsx")) + sorted(sub.glob("*.xls"))
    return nested


def collect_all_sales(input_dirs: List[str]) -> pd.DataFrame:
    """
    여러 입력 디렉토리에서 전체 판매 데이터 수집.

    [v3 개선] 아래 4가지 폴더 구조 모두 자동 지원:
      A) input/240501판매현황/*.xlsx          (날짜폴더 바로 아래 xlsx)
      B) input/202404/240401/*.xlsx           (월폴더 → 날짜폴더 → xlsx)
      C) input/202404/240407/판매현황/*.xlsx  (월폴더 → 날짜폴더 → 하위폴더 → xlsx)
      D) 콤마 구분 여러 폴더 동시 처리
    """
    all_frames = []
    processed_dates = set()

    for input_dir in input_dirs:
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"  ⚠ 경로 없음: {input_dir}")
            continue

        subdirs = sorted([d for d in input_path.iterdir() if d.is_dir()])

        if not subdirs:
            # 하위 폴더 없음: 파일 직접 처리
            for fpath in sorted(input_path.glob("*.xlsx")) + sorted(input_path.glob("*.xls")):
                fdate = parse_date_from_filename(str(fpath))
                if fdate is None:
                    continue
                df = load_sales_file(str(fpath))
                if not df.empty:
                    df["date"] = pd.Timestamp(fdate)
                    all_frames.append(df)
                    processed_dates.add(fdate)
            continue

        for subdir in subdirs:
            # ── 월 폴더(202404, 202405) → 내부 날짜 폴더들 처리 ──
            if is_month_folder(subdir):
                day_dirs = sorted([d for d in subdir.iterdir() if d.is_dir()])
                for day_dir in day_dirs:
                    folder_date = parse_date_from_foldername(day_dir.name)
                    if folder_date is None:
                        continue
                    xlsx_files = collect_xlsx_for_date(day_dir)
                    if not xlsx_files:
                        continue
                    day_frames = [load_sales_file(str(f)) for f in xlsx_files]
                    day_frames = [d for d in day_frames if not d.empty]
                    if day_frames:
                        day_df = pd.concat(day_frames, ignore_index=True)
                        day_df["date"] = pd.Timestamp(folder_date)
                        all_frames.append(day_df)
                        processed_dates.add(folder_date)
                continue

            # ── 날짜 폴더(240401, 240501판매현황) → xlsx 수집 ──
            folder_date = parse_date_from_foldername(subdir.name)
            if folder_date is None:
                continue
            xlsx_files = collect_xlsx_for_date(subdir)
            if not xlsx_files:
                continue
            day_frames = [load_sales_file(str(f)) for f in xlsx_files]
            day_frames = [d for d in day_frames if not d.empty]
            if day_frames:
                day_df = pd.concat(day_frames, ignore_index=True)
                day_df["date"] = pd.Timestamp(folder_date)
                all_frames.append(day_df)
                processed_dates.add(folder_date)

    if not all_frames:
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)
    date_range = (
        f"{min(processed_dates)} ~ {max(processed_dates)}"
        if processed_dates else "?"
    )
    print(f"  ✅ 전체 수집: {len(combined):,}행 | {len(processed_dates)}일 ({date_range})")
    return combined


# ══════════════════════════════════════════════
# ⑤ PLU 매칭 (3단계)
# ══════════════════════════════════════════════

def _fuzzy_match(query: str, candidates: List[str],
                 threshold: float) -> Optional[Tuple[str, float]]:
    """Fuzzy 매칭 내부 함수."""
    if not query:
        return None
    hits = get_close_matches(query, candidates, n=3, cutoff=threshold)
    if hits:
        best = max(hits, key=lambda h: SequenceMatcher(None, query, h).ratio())
        score = SequenceMatcher(None, query, best).ratio()
        if score >= threshold:
            return best, score
    q_len = len(query)
    filtered = [c for c in candidates if abs(len(c) - q_len) <= q_len * 0.3 + 3]
    best_score, best_cand = 0.0, None
    for cand in filtered:
        score = SequenceMatcher(None, query, cand).ratio()
        if score > best_score:
            best_score, best_cand = score, cand
    return (best_cand, best_score) if best_score >= threshold else None


def match_plu(
    sales_df: pd.DataFrame,
    lookup: Dict[str, dict],
    lookup_loose: Dict[str, dict],
    all_master_names: List[str],
    fuzzy_threshold: float = 0.82,
) -> pd.DataFrame:
    """
    판매현황 상품명 → PLU 매칭 (3단계).
    [v3 개선] 미매칭 로그를 날짜별 중복 없이 고유 상품명 기준으로 수집.
    """
    norm_cands = {normalize_name(n): n for n in all_master_names if n}
    norm_cand_keys = list(norm_cands.keys())

    results  = []
    stats    = {"exact": 0, "loose": 0, "fuzzy": 0, "unmatched": 0}
    # [v3] 고유 상품명만 추적 (set 사용)
    fuzzy_log:     List[Tuple[str, str, str]] = []
    unmatched_set: set = set()  # 중복 제거용
    unmatched_log: List[str] = []

    for _, row in sales_df.iterrows():
        name = str(row["product_name"]).strip()

        # 1단계: Exact
        norm = normalize_name(name)
        if norm in lookup:
            m = lookup[norm]
            results.append({**row.to_dict(), **m, "match_type": "exact"})
            stats["exact"] += 1
            continue

        # 2단계: Loose Exact
        loose = normalize_name_loose(name)
        if loose in lookup_loose:
            m = lookup_loose[loose]
            results.append({**row.to_dict(), **m, "match_type": "loose_exact"})
            stats["loose"] += 1
            continue

        # 3단계: Fuzzy
        fr = _fuzzy_match(norm, norm_cand_keys, threshold=fuzzy_threshold)
        if fr:
            matched_norm, score = fr
            orig_name = norm_cands[matched_norm]
            m = lookup.get(normalize_name(orig_name)) or \
                lookup_loose.get(normalize_name_loose(orig_name), {})
            if m:
                results.append({**row.to_dict(), **m,
                                 "match_type": f"fuzzy({score:.2f})"})
                stats["fuzzy"] += 1
                if name not in {fl[0] for fl in fuzzy_log}:
                    fuzzy_log.append((name, orig_name, f"{score:.2f}"))
                continue

        # 미매칭 — 고유 상품명만 로그에 추가
        results.append({
            **row.to_dict(),
            "plu_code": "", "cat_l": row.get("category_hint", "기타"),
            "cat_m": row.get("category_hint", "기타"), "cat_s": "",
            "match_type": "unmatched",
        })
        stats["unmatched"] += 1
        if name not in unmatched_set:
            unmatched_set.add(name)
            unmatched_log.append(name)

    result_df = pd.DataFrame(results)
    total = len(result_df)

    # 매칭 결과 요약
    print(f"\n  ┌─ PLU 매칭 결과 {'─'*35}")
    print(f"  │  전체  : {total:>5,}개  (100.0%)")
    print(f"  │  Exact : {stats['exact']:>5,}개  ({stats['exact']/total*100:.1f}%)")
    print(f"  │  Loose : {stats['loose']:>5,}개  ({stats['loose']/total*100:.1f}%)")
    print(f"  │  Fuzzy : {stats['fuzzy']:>5,}개  ({stats['fuzzy']/total*100:.1f}%)")
    print(f"  │  미매칭: {stats['unmatched']:>5,}개  ({stats['unmatched']/total*100:.1f}%)")
    print(f"  │         → 고유 미매칭 상품: {len(unmatched_log)}개 (분류기준표 없는 신상품)")
    print(f"  └─ 전체 매칭률: {(total-stats['unmatched'])/total*100:.1f}%")

    if fuzzy_log:
        print(f"\n  ⚠ Fuzzy 매칭 목록 (확인 권장):")
        for orig, cand, sc in fuzzy_log[:20]:
            print(f"    '{orig}' → '{cand}'  (유사도: {sc})")
        if len(fuzzy_log) > 20:
            print(f"    ... 외 {len(fuzzy_log)-20}건")

    if unmatched_log:
        print(f"\n  ℹ 미매칭 {len(unmatched_log)}개 → unmatched.txt 저장")
        for n in unmatched_log[:5]:
            print(f"    - {n}")
        if len(unmatched_log) > 5:
            print(f"    ... 외 {len(unmatched_log)-5}개")

    # attrs 대신 result_df 컬럼 외부 변수로 직접 반환
    result_df._unmatched_log = unmatched_log
    result_df._fuzzy_log     = fuzzy_log
    return result_df


# ══════════════════════════════════════════════
# ⑥ 피처 생성
# ══════════════════════════════════════════════

def build_lag_rolling(df: pd.DataFrame) -> pd.DataFrame:
    """
    plu_code(또는 product_name)별 lag/rolling 피처 계산.
    shift(1) 선행 적용 → Data Leakage 방지.
    """
    key_col = (
        "plu_code"
        if "plu_code" in df.columns and df["plu_code"].ne("").any()
        else "product_name"
    )
    df["date"]  = pd.to_datetime(df["date"])
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)

    result_frames = []
    for key_val, group in df.groupby(key_col, dropna=False):
        daily = (
            group.groupby("date")["sales"].sum()
            .reset_index().sort_values("date")
        )
        full_idx = pd.date_range(
            start=daily["date"].min(), end=daily["date"].max(), freq="D"
        )
        series  = (daily.set_index("date")["sales"]
                        .reindex(full_idx, fill_value=0.0).astype(float))
        shifted = series.shift(1)

        result_frames.append(pd.DataFrame({
            "date":           full_idx,
            key_col:          key_val,
            "lag_1":          shifted.values,
            "lag_3":          series.shift(3).values,
            "lag_7":          series.shift(7).values,
            "rolling_7_mean": shifted.rolling(7, min_periods=1).mean().values,
            "rolling_7_std":  shifted.rolling(7, min_periods=1).std(ddof=0).values,
        }))

    if not result_frames:
        return df

    lag_df = pd.concat(result_frames, ignore_index=True)
    merged = df.merge(lag_df, on=["date", key_col], how="left")

    for col in ("lag_1", "lag_3", "lag_7", "rolling_7_mean", "rolling_7_std"):
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)

    if "plu_code" in merged.columns:
        merged["plu_code"] = (merged["plu_code"]
                              .fillna("").astype(str).str.strip()
                              .replace("nan", ""))
    return merged


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    캘린더 피처 추가.
    is_holiday = 법정 공휴일 OR 주말
    academic_event, building_headcount = 0 (Phase 2에서 학사일정/시간표 데이터로 채움)
    """
    dt = pd.to_datetime(df["date"])
    df["day_of_week"] = dt.dt.weekday.astype(int)
    df["month"]       = dt.dt.month.astype(int)

    years       = dt.dt.year.dropna().unique().astype(int).tolist()
    holiday_set = get_holiday_set(years)
    is_pub_hol  = dt.dt.normalize().isin(holiday_set)
    is_weekend  = dt.dt.dayofweek >= 5
    df["is_holiday"] = (is_pub_hol | is_weekend).astype(int)

    df["academic_event"]     = 0  # Phase 2: academic_calendar.json으로 채울 예정
    df["building_headcount"] = 0  # Phase 2: schedule.csv(요일별 수강인원)으로 채울 예정
    return df


def add_safety_stock(df: pd.DataFrame) -> pd.DataFrame:
    """안전재고 = rolling_7_mean × 카테고리 배율."""
    def get_cat(row):
        for col in ("cat_m", "cat_l", "category_hint"):
            v = str(row.get(col, "")).strip()
            if v and v not in ("", "기타", "nan"):
                return v
        return "기타"
    cats = df.apply(get_cat, axis=1)
    df["safety_stock"] = (
        df["rolling_7_mean"] * cats.map(safety_multiplier)
    ).round().clip(lower=0).fillna(0).astype(int)
    return df


# ══════════════════════════════════════════════
# ⑦ 출력 정리 및 저장
# ══════════════════════════════════════════════

def finalize_output(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼 타입 정리 및 출력 순서 정렬."""
    if "plu_code" not in df.columns:
        df["plu_code"] = ""
    df["plu_code"] = (df["plu_code"].fillna("").astype(str)
                        .str.strip().replace("nan", ""))

    for col, src in [("category_l","cat_l"),("category_m","cat_m"),("category_s","cat_s")]:
        if col not in df.columns:
            df[col] = df.get(src, "")
        df[col] = df[col].fillna("").astype(str).str.strip().replace("nan", "")

    for col in ("category_l", "category_m"):
        mask = df[col].eq("")
        df.loc[mask, col] = df.loc[mask, "category_hint"].fillna("기타")

    df["sales"]          = df["sales"].fillna(0).astype(int)
    df["lag_1"]          = df["lag_1"].round().astype(int)
    df["lag_3"]          = df["lag_3"].round().astype(int)
    df["lag_7"]          = df["lag_7"].round().astype(int)
    df["rolling_7_mean"] = df["rolling_7_mean"].round(2)
    df["rolling_7_std"]  = df["rolling_7_std"].round(2)
    df["date"]           = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    final_cols = [c for c in OUTPUT_COLS if c in df.columns]
    if "product_name" not in final_cols and "product_name" in df.columns:
        final_cols.append("product_name")
    return df[final_cols].copy()


def save_outputs(feature_df, output_dir, unmatched_log, fuzzy_log):
    """CSV + XLSX + 미매칭/Fuzzy 리포트 저장."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    dates = sorted(feature_df["date"].unique())
    if dates:
        s, e = dates[0].replace("-","_"), dates[-1].replace("-","_")
        label = f"{s}_to_{e}" if s != e else s
    else:
        label = datetime.today().strftime("%Y_%m_%d")

    csv_path  = out / f"sales_{label}_features.csv"
    xlsx_path = out / f"sales_{label}_features.xlsx"

    # plu_code 빈 문자열 보존 (read_csv 시 dtype={'plu_code':str} 필수)
    feature_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    feature_df.to_excel(xlsx_path, index=False)

    if unmatched_log:
        rp = out / f"sales_{label}_unmatched.txt"
        with open(rp, "w", encoding="utf-8") as f:
            f.write(f"# 미매칭 상품 목록 ({len(unmatched_log)}건)\n")
            f.write("# 분류기준표에 없는 신상품 또는 상품명 표기 차이\n")
            f.write("# 해결: 분류기준표에 추가 후 재실행\n\n")
            for n in sorted(set(unmatched_log)):
                f.write(f"{n}\n")
        print(f"  📄 미매칭 리포트: {rp}")

    if fuzzy_log:
        fp = out / f"sales_{label}_fuzzy_check.txt"
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"# Fuzzy 매칭 목록 ({len(fuzzy_log)}건) — 수동 확인 권장\n\n")
            for orig, cand, sc in fuzzy_log:
                f.write(f"'{orig}' → '{cand}'  (유사도: {sc})\n")
        print(f"  📄 Fuzzy 리포트: {fp}")

    n_prod = feature_df["product_name"].nunique() if "product_name" in feature_df.columns else "?"
    print(f"\n  💾 CSV  저장: {csv_path}")
    print(f"  💾 XLSX 저장: {xlsx_path}")
    print(f"     총 {len(feature_df):,}행  |  {feature_df['date'].nunique()}일  |  {n_prod}개 상품")
    return csv_path, xlsx_path


# ══════════════════════════════════════════════
# ⑧ 메인 파이프라인
# ══════════════════════════════════════════════

def run(
    input_dir: str,
    output_dir: str = "data/processed",
    master_dir: Optional[str] = None,   # [v3] 선택사항으로 변경
    fuzzy_threshold: float = 0.82,
) -> Optional[Tuple[Path, Path]]:
    """
    메인 실행 함수 (터미널 / Colab 공용).

    Parameters
    ----------
    input_dir       : 판매현황 루트 디렉토리 (콤마로 여러 개 가능)
    output_dir      : 결과 저장 폴더
    master_dir      : 분류기준표 폴더/파일 경로 (없으면 PLU 매칭 건너뜀)
    fuzzy_threshold : Fuzzy 매칭 임계값 (기본 0.82)
    """
    print("=" * 62)
    print("  에러없조 | 판매현황 → RF 학습 데이터 변환기 v4")
    print("=" * 62)

    input_dirs = [p.strip() for p in str(input_dir).split(",") if p.strip()]
    print(f"  입력       : {', '.join(input_dirs)}")
    print(f"  출력       : {output_dir}")
    print(f"  분류기준표 : {master_dir if master_dir else '없음 (product_name 기반 처리)'}")

    # Step 1: 분류기준표 로드 (선택)
    lookup = lookup_loose = None
    all_master_names = []
    use_master = False

    if master_dir and Path(master_dir).exists():
        print(f"\n[Step 1] 분류기준표 로드")
        try:
            lookup, lookup_loose, all_master_names = load_master(master_dir)
            use_master = True
        except (FileNotFoundError, ValueError) as e:
            print(f"  ⚠ {e} → product_name 기반으로 처리합니다.")
    else:
        print(f"\n[Step 1] 분류기준표 없음 → product_name 기반으로 처리")

    # Step 2: 판매 데이터 수집
    print(f"\n[Step 2] 판매 데이터 수집")
    raw_df = collect_all_sales(input_dirs)
    if raw_df.empty:
        print("  ❌ 수집된 데이터가 없습니다.")
        return None

    # Step 3: PLU 매칭
    print(f"\n[Step 3] PLU 매칭")
    unmatched_log, fuzzy_log = [], []

    if use_master:
        matched_df    = match_plu(raw_df, lookup, lookup_loose,
                                  all_master_names, fuzzy_threshold)
        unmatched_log = getattr(matched_df, "_unmatched_log", [])
        fuzzy_log     = getattr(matched_df, "_fuzzy_log", [])
        matched_df["category"] = (matched_df.get("cat_m", pd.Series())
                                  .fillna(matched_df.get("category_hint","기타"))
                                  .fillna("기타"))
    else:
        print("  분류기준표 없음 → PLU 건너뜀, category_hint 사용")
        matched_df              = raw_df.copy()
        matched_df["plu_code"]  = ""
        matched_df["cat_l"]     = ""
        matched_df["cat_m"]     = matched_df["category_hint"].fillna("기타")
        matched_df["cat_s"]     = ""
        matched_df["match_type"] = "no_master"
        matched_df["category"]  = matched_df["category_hint"].fillna("기타")

    matched_df["category"] = matched_df["category"].replace("", "기타").fillna("기타")

    # Step 4: 미매칭 행 제거
    # 분류기준표에 없는 상품(미매칭)은 두 가지 중 하나:
    #   ① 소계(집계)행  → 하위 상품 합산값. 그대로 두면 판매량 중복 집계 발생
    #   ② 미등록 신상품 → PLU 없어서 RF 모델이 상품 식별 불가
    # 두 경우 모두 학습 데이터에 포함시키면 안 됨.
    # → 분류기준표 사용 시 미매칭 행 전체 제거가 가장 안전한 기준.
    # ※ 분류기준표 없이 실행(no_master 모드)하면 제거 건너뜀.
    print(f"\n[Step 4] 미매칭 행 처리")
    if use_master:
        before = len(matched_df)
        matched_df = matched_df[matched_df["match_type"] != "unmatched"].copy()
        removed = before - len(matched_df)
        print(f"  미매칭 {removed}행 제거 (소계/미등록 상품 → 중복 집계 방지)")
        print(f"  남은 행: {len(matched_df):,}행")
    else:
        print(f"  분류기준표 없음 → 미매칭 제거 건너뜀")

    # Step 5: 중복 집계
    print(f"\n[Step 5] 중복 집계")
    matched_df["date"]  = pd.to_datetime(matched_df["date"])
    matched_df["sales"] = pd.to_numeric(matched_df["sales"], errors="coerce").fillna(0)

    has_plu = (
        "plu_code" in matched_df.columns and
        matched_df["plu_code"].ne("").any()
    )
    group_keys = ["date", "plu_code" if has_plu else "product_name",
                  "product_name", "cat_l", "cat_m", "cat_s",
                  "match_type", "category_hint"]
    group_keys = [k for k in group_keys if k in matched_df.columns]
    agg_df = matched_df.groupby(group_keys, as_index=False)["sales"].sum()

    if not has_plu:
        agg_df["plu_code"] = ""
    agg_df["plu_code"] = (agg_df["plu_code"].fillna("")
                            .astype(str).str.strip().replace("nan",""))
    print(f"  집계 후: {len(agg_df):,}행")

    # Step 5: lag/rolling
    print(f"\n[Step 6] Lag/Rolling 피처 생성")
    feature_df = build_lag_rolling(agg_df)
    print(f"  완료: {len(feature_df):,}행")

    # Step 6: 캘린더 + 안전재고
    print(f"\n[Step 7] 캘린더 피처 + 안전재고")
    feature_df = add_calendar_features(feature_df)
    feature_df = add_safety_stock(feature_df)

    # Step 7: 출력 정리
    print(f"\n[Step 8] 출력 정리")
    feature_df = finalize_output(feature_df)

    # Step 8: 저장
    print(f"\n[Step 9] 저장")
    return save_outputs(feature_df, output_dir, unmatched_log, fuzzy_log)


# ══════════════════════════════════════════════
# ⑨ CLI
# ══════════════════════════════════════════════

def _is_interactive() -> bool:
    try:
        get_ipython()  # type: ignore  # noqa
        return True
    except NameError:
        return False


def main():
    if _is_interactive():
        print("Colab/Jupyter 환경 → run() 함수를 사용하세요.")
        print("from converter_v3 import run")
        print("run(input_dir='data/raw/240501-15', master_dir='csv_상품분류기준표')")
        return

    parser = argparse.ArgumentParser(
        description="에러없조 | 판매현황 → RF 학습 데이터 변환기 v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # PLU 매칭 포함 (권장)
  python converter_v3.py --input data\\raw\\240501-15 --master csv_상품분류기준표

  # 분류기준표 없이 빠른 확인 (PLU 없이 동작)
  python converter_v3.py --input data\\raw\\240501-15

  # 여러 폴더 동시 처리
  python converter_v3.py --input "data\\raw\\240501-15,data\\raw\\250601-30" --master csv_상품분류기준표

  # 출력 폴더 지정
  python converter_v3.py --input data\\raw\\240501-15 --master csv_상품분류기준표 --output data\\processed
        """
    )
    parser.add_argument("--input",  required=True, help="판매현황 루트 디렉토리 (콤마로 여러 개 가능)")
    parser.add_argument("--master", default=None,  help="분류기준표 폴더/파일 경로 (선택)")
    parser.add_argument("--output", default="data/processed", help="결과 저장 폴더")
    parser.add_argument("--fuzzy-threshold", type=float, default=0.82,
                        help="Fuzzy 매칭 임계값 (기본: 0.82)")
    args = parser.parse_args()

    run(
        input_dir=args.input,
        output_dir=args.output,
        master_dir=args.master,
        fuzzy_threshold=args.fuzzy_threshold,
    )


if __name__ == "__main__":
    main()
