"""
converter.py — 일별 판매현황 xlsx → PLU 매칭 → ML-ready CSV/XLSX 변환기

━━━ 터미널(로컬) 사용법 ━━━
    python converter.py --sales <판매현황.xlsx> --master <분류기준표.csv 또는 xlsx>
    python converter.py --sales data/raw/sales_2026_04_01/testX.xlsx --master data/분류기준표.csv

━━━ Google Colab 사용법 ━━━
    # 셀 1: 파일 업로드 또는 Google Drive 마운트
    # 셀 2: 아래처럼 run() 함수 직접 호출
    from converter import run
    run(
        sales="판매현황_2026_04_01.xlsx",
        master="분류기준표.csv",
        force=False,
        fuzzy_threshold=0.75,
    )

출력:
    data/processed/sales_YYYY_MM_DD_matched.csv   (utf-8-sig, ML 입력용)
    data/processed/sales_YYYY_MM_DD_matched.xlsx  (검토용)
    data/processed/sales_YYYY_MM_DD_unmatched.txt (미매칭 항목 목록)
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import re

import pandas as pd
from difflib import SequenceMatcher, get_close_matches

# ──────────────────────────────────────────────
# 소계(분류) 행 필터 — plu코드매칭프롬프트.txt 기준
# ──────────────────────────────────────────────
SKIP_ROWS = {
    "밥류", "도시락", "정찬도시락", "덮밥/초밥", "주문도시락",
    "김밥", "줄김밥", "용기/대용량김밥",
    "주먹밥", "일반삼각", "더큰삼각", "기타주먹밥",
}

# 최종 출력 컬럼 순서
FINAL_COLS = (
    ["PLU코드", "상품명", "대분류", "중분류", "소분류", "매출합계", "매출평균"]
    + [f"{h:02d}H" for h in range(24)]
)

HOUR_COLS = [f"{h:02d}H" for h in range(24)]  # 00H ~ 23H


# ──────────────────────────────────────────────
# 유틸 함수
# ──────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """공백 제거 후 소문자 통일 — 매칭 키로만 사용, 출력엔 원본 유지"""
    if not isinstance(name, str):
        return ""
    return re.sub(r"\s+", "", name.strip())


def normalize_plu(plu) -> str:
    """
    xlsx 파일에서 읽을 때만 적용하는 PLU 정규화.
    - dtype=str 로 읽은 뒤 소수점/과학적표기법 제거
    예) "1234.0" → "1234", "1.23e3" → "1230" 처리
    Spring Boot API 레이어에는 절대 적용하지 않음.
    """
    if not isinstance(plu, str):
        return ""
    plu = plu.strip()
    # 과학적 표기법 처리: 1.23E+03 → 1230
    if re.match(r"^[\d.]+[eE][+\-]?\d+$", plu):
        try:
            plu = str(int(float(plu)))
        except Exception:
            pass
    # 소수점 제거: 1234.0 → 1234
    plu = plu.split(".")[0]
    return plu.strip()


def load_master(path: str) -> pd.DataFrame:
    """
    분류기준표 로드 (CSV 또는 xlsx).
    반드시 dtype=str 옵션 적용.
    헤더는 4번째 행(index 3) 에 있는 경우를 자동 감지.
    필수 컬럼: PLU코드, 상품명, 대분류, 중분류, 소분류
    """
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        # 헤더 자동 감지: row 0~5 범위에서 'PLU' 포함 행 찾기
        probe = pd.read_excel(path, header=None, nrows=10, dtype=str)
        header_row = 0
        for i, row in probe.iterrows():
            if any("PLU" in str(v).upper() for v in row.values):
                header_row = i
                break
        df = pd.read_excel(path, header=header_row, dtype=str)
    else:
        # CSV: 헤더 자동 감지
        probe = pd.read_csv(path, header=None, nrows=10, dtype=str, encoding="utf-8-sig")
        header_row = 0
        for i, row in probe.iterrows():
            if any("PLU" in str(v).upper() for v in row.values):
                header_row = i
                break
        df = pd.read_csv(path, header=header_row, dtype=str, encoding="utf-8-sig")

    # 컬럼명 공백 제거
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")

    # PLU 정규화 (xlsx/csv 읽기 전용)
    plu_col = next((c for c in df.columns if "PLU" in c.upper()), None)
    name_col = next((c for c in df.columns if "상품명" in c), None)

    if plu_col is None or name_col is None:
        raise ValueError(f"분류기준표에서 PLU 또는 상품명 컬럼을 찾을 수 없습니다.\n현재 컬럼: {list(df.columns)}")

    df[plu_col] = df[plu_col].apply(normalize_plu)
    df["__norm_name"] = df[name_col].apply(normalize_name)

    # 분류 컬럼 확인
    for col in ["대분류", "중분류", "소분류"]:
        if col not in df.columns:
            df[col] = ""

    # 중복 PLU 처리: 동일 상품명에 PLU 중복 시 가장 큰 값 사용
    dup_names = df[df.duplicated(subset=[name_col], keep=False)]
    if not dup_names.empty:
        print("\n[중복 상품명 감지]")
        for nm, grp in dup_names.groupby(name_col):
            cats = grp[["대분류", "중분류", "소분류"]].drop_duplicates()
            if len(cats) > 1:
                print(f"  ⚠ '{nm}': 동일 상품명에 분류가 다릅니다!")
                print(cats.to_string(index=False))

        # 숫자 변환 가능한 PLU만 비교 — 최대값 선택
        def safe_int(v):
            try:
                return int(v)
            except Exception:
                return -1

        df["__plu_int"] = df[plu_col].apply(safe_int)
        df = df.sort_values("__plu_int", ascending=False)
        df = df.drop_duplicates(subset=[name_col], keep="first")
        df = df.drop(columns=["__plu_int"])

    df = df.reset_index(drop=True)
    print(f"✅ 분류기준표 로드 완료: {len(df):,}개 상품")
    return df, plu_col, name_col


def _detect_header_row(raw: pd.DataFrame) -> int:
    """
    '상품명' 또는 '품명' 이 들어있는 행을 헤더 행으로 자동 감지.
    없으면 0 반환.
    """
    for i in range(min(10, len(raw))):
        row_vals = [str(v) for v in raw.iloc[i].values]
        if any("상품명" in v or "품명" in v for v in row_vals):
            return i
    return 0


def load_sales(path: str) -> pd.DataFrame:
    """
    판매현황 xlsx 로드 — 파일 포맷 자동 감지.

    지원 포맷:
      A) iMart24 원본: row 0~4 헤더영역, row 5~ 데이터,
         col 0=번호, col 1=상품명, col 2=매출합계, col 3=매출평균, col 4~27=00H~23H (28컬럼)
      B) 단순 포맷: 상품명/매출합계/매출평균만 있는 축약 파일 (7컬럼 이하)
         → 시간대 컬럼은 0으로 채워서 생성

    반드시 dtype=str 로 읽음.
    """
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        raw = pd.read_excel(path, header=None, dtype=str)
    else:
        raw = pd.read_csv(path, header=None, dtype=str, encoding="utf-8-sig")

    # ── 파일 구조 출력 (디버그용) ──────────────────────
    print(f"\n[파일 구조 분석]")
    print(f"  전체 크기: {raw.shape[0]}행 × {raw.shape[1]}열")
    print(f"  상위 6행 미리보기:")
    print(raw.head(6).to_string())
    print()

    # ── 헤더 행 자동 감지 ──────────────────────────────
    header_row = _detect_header_row(raw)

    if header_row > 0:
        # 헤더가 중간 행에 있는 경우 (iMart24 원본 스타일)
        data = raw.iloc[header_row + 2:].reset_index(drop=True)  # 헤더 다음다음 행부터 데이터
        ncols = data.shape[1]
    else:
        # 헤더가 없거나 첫 행이 헤더인 경우
        # 첫 행이 컬럼명인지 확인
        first_row = [str(v) for v in raw.iloc[0].values]
        if any("상품명" in v or "품명" in v for v in first_row):
            data = raw.iloc[1:].reset_index(drop=True)
        else:
            data = raw.copy()
        ncols = data.shape[1]

    print(f"  데이터 시작 행: {header_row + 2 if header_row > 0 else 1}")
    print(f"  데이터 컬럼 수: {ncols}")

    # ── 포맷 A: 28컬럼 이상 (iMart24 원본, 시간대 포함) ─
    if ncols >= 28:
        col_names = (
            ["idx", "상품명", "매출합계", "매출평균"]
            + HOUR_COLS
            + [f"extra_{i}" for i in range(ncols - 28)]
        )
        data.columns = col_names[:ncols]
        keep = ["상품명", "매출합계", "매출평균"] + HOUR_COLS
        data = data[keep]
        has_hours = True

    # ── 포맷 B: 컬럼 수 부족 → 상품명 컬럼 자동 탐지 ──
    else:
        # 상품명 컬럼 위치 탐지: 가장 많은 문자열이 들어있는 컬럼
        name_col_idx = None
        sum_col_idx = None
        avg_col_idx = None

        # 헤더 키워드로 컬럼 위치 파악
        header_vals = [str(v) for v in raw.iloc[header_row].values] if header_row < len(raw) else []
        for i, v in enumerate(header_vals):
            if "상품명" in v or "품명" in v:
                name_col_idx = i
            elif "합계" in v or "매출합계" in v:
                sum_col_idx = i
            elif "평균" in v or "매출평균" in v:
                avg_col_idx = i

        # 못 찾으면 위치 추측 (번호-상품명-합계-평균 순)
        if name_col_idx is None:
            name_col_idx = 1 if ncols > 1 else 0
        if sum_col_idx is None:
            sum_col_idx = 2 if ncols > 2 else name_col_idx + 1
        if avg_col_idx is None:
            avg_col_idx = 3 if ncols > 3 else sum_col_idx + 1

        print(f"  → 포맷 B 감지: 상품명={name_col_idx}번, 합계={sum_col_idx}번, 평균={avg_col_idx}번 컬럼")

        data = data.rename(columns={
            data.columns[name_col_idx]: "상품명",
            data.columns[sum_col_idx]:  "매출합계",
        })
        if avg_col_idx < ncols:
            data = data.rename(columns={data.columns[avg_col_idx]: "매출평균"})
        else:
            data["매출평균"] = "0"

        # 시간대 컬럼 없으므로 0으로 채움
        for h in HOUR_COLS:
            data[h] = "0"
        has_hours = False
        print(f"  ⚠ 시간대(00H~23H) 컬럼 없음 → 모두 0으로 채웁니다.")

    # ── 공통: 공백·소계 행 제거 ────────────────────────
    data = data.dropna(subset=["상품명"])
    data["상품명"] = data["상품명"].astype(str).str.strip()
    data = data[data["상품명"] != ""]
    data = data[data["상품명"] != "nan"]
    data = data[~data["상품명"].isin(SKIP_ROWS)]
    data = data.reset_index(drop=True)

    # 숫자 컬럼 — 정수형으로 변환 (NaN → 0)
    for col in ["매출합계", "매출평균"] + HOUR_COLS:
        data[col] = (
            pd.to_numeric(data[col], errors="coerce")
            .fillna(0)
            .round()
            .astype(int)
        )

    print(f"✅ 판매현황 로드 완료: {len(data):,}개 상품")
    return data


# ──────────────────────────────────────────────
# 매칭 엔진
# ──────────────────────────────────────────────

def fuzzy_match(name: str, candidates: list, threshold: float = 0.75) -> str | None:
    """
    difflib SequenceMatcher 기반 퍼지 매칭.
    정규화된 이름으로 비교하되 threshold 이상인 최고 유사도 항목 반환.
    """
    norm = normalize_name(name)
    if not norm:
        return None
    norm_cands = {normalize_name(c): c for c in candidates}
    matches = get_close_matches(norm, list(norm_cands.keys()), n=1, cutoff=threshold)
    if matches:
        return norm_cands[matches[0]]
    # get_close_matches cutoff 미달 시 수동 스코어 계산
    best_score = 0.0
    best_cand = None
    for nc, orig in norm_cands.items():
        score = SequenceMatcher(None, norm, nc).ratio()
        if score > best_score:
            best_score = score
            best_cand = orig
    if best_score >= threshold:
        return best_cand
    return None


def match_products(sales: pd.DataFrame, master: pd.DataFrame, plu_col: str, name_col: str) -> pd.DataFrame:
    """
    판매현황 × 분류기준표 매칭.
    1차: 정규화 이름 정확 매칭
    2차: difflib 퍼지 매칭 (유사도 0.75 이상)
    """
    # 마스터 조회 딕셔너리 (정규화명 → row)
    master_lookup: dict[str, dict] = {}
    for _, row in master.iterrows():
        key = row["__norm_name"]
        if key:
            master_lookup[key] = {
                "PLU코드": row[plu_col],
                "대분류": row.get("대분류", ""),
                "중분류": row.get("중분류", ""),
                "소분류": row.get("소분류", ""),
                "원본상품명": row[name_col],
            }

    results = []
    unmatched = []
    fuzzy_matched = []

    for _, srow in sales.iterrows():
        name = srow["상품명"]
        norm = normalize_name(name)

        # 1차: 정확 매칭
        if norm in master_lookup:
            m = master_lookup[norm]
            results.append({
                "PLU코드": m["PLU코드"],
                "상품명": name,
                "대분류": m["대분류"],
                "중분류": m["중분류"],
                "소분류": m["소분류"],
                "매출합계": srow["매출합계"],
                "매출평균": srow["매출평균"],
                **{h: srow[h] for h in HOUR_COLS},
                "__match_type": "exact",
            })
        else:
            # 2차: 퍼지 매칭
            fuzzy_cand = fuzzy_match(name, [v["원본상품명"] for v in master_lookup.values()])
            if fuzzy_cand:
                fuzzy_norm = normalize_name(fuzzy_cand)
                m = master_lookup[fuzzy_norm]
                score = SequenceMatcher(None, norm, fuzzy_norm).ratio()
                results.append({
                    "PLU코드": m["PLU코드"],
                    "상품명": name,
                    "대분류": m["대분류"],
                    "중분류": m["중분류"],
                    "소분류": m["소분류"],
                    "매출합계": srow["매출합계"],
                    "매출평균": srow["매출평균"],
                    **{h: srow[h] for h in HOUR_COLS},
                    "__match_type": f"fuzzy({score:.2f})→{fuzzy_cand}",
                })
                fuzzy_matched.append((name, fuzzy_cand, f"{score:.2f}"))
            else:
                results.append({
                    "PLU코드": "",
                    "상품명": name,
                    "대분류": "",
                    "중분류": "",
                    "소분류": "",
                    "매출합계": srow["매출합계"],
                    "매출평균": srow["매출평균"],
                    **{h: srow[h] for h in HOUR_COLS},
                    "__match_type": "unmatched",
                })
                unmatched.append(name)

    df_result = pd.DataFrame(results)
    return df_result, unmatched, fuzzy_matched


# ──────────────────────────────────────────────
# 검증 보고
# ──────────────────────────────────────────────

def report(df: pd.DataFrame, unmatched: list, fuzzy_matched: list) -> bool:
    total = len(df)
    n_exact = (df["__match_type"] == "exact").sum()
    n_fuzzy = df["__match_type"].str.startswith("fuzzy").sum()
    n_unmatched = (df["__match_type"] == "unmatched").sum()

    print("\n" + "="*55)
    print("  📊 매칭 결과 보고")
    print("="*55)
    print(f"  총 상품 수       : {total:>5}개")
    print(f"  정확 매칭        : {n_exact:>5}개  ({n_exact/total*100:.1f}%)")
    print(f"  퍼지 매칭        : {n_fuzzy:>5}개  ({n_fuzzy/total*100:.1f}%)")
    print(f"  매칭 실패        : {n_unmatched:>5}개  ({n_unmatched/total*100:.1f}%)")
    print(f"  전체 매칭률      : {(total-n_unmatched)/total*100:.1f}%")
    print("="*55)

    if fuzzy_matched:
        print("\n⚠  퍼지 매칭 항목 (확인 권장):")
        for orig, cand, score in fuzzy_matched:
            print(f"   '{orig}' → '{cand}'  (유사도: {score})")

    if unmatched:
        print(f"\n❌ 매칭 실패 {len(unmatched)}개:")
        for u in unmatched:
            print(f"   - {u}")
        print("\n  → 해결 방법:")
        print("  1) 분류기준표에 해당 상품명을 직접 추가")
        print("  2) PLU_매칭_변환기.xlsx의 '4_수동보정' 시트에서 PLU 직접 입력")
        print("  3) 이 스크립트에 --force 플래그를 붙여 미매칭 포함 저장")
        return False

    print("\n✅ 매칭 실패 0건 — CSV/XLSX 생성 가능")
    return True


# ──────────────────────────────────────────────
# 저장
# ──────────────────────────────────────────────

def save_outputs(df: pd.DataFrame, sales_path: str, unmatched: list, force: bool):
    """결과를 CSV + XLSX 로 저장"""
    # 날짜 추출: 파일명에서 YYYY_MM_DD 또는 YYYYMMDD 찾기
    stem = Path(sales_path).stem
    date_match = re.search(r"(\d{4})[_\-]?(\d{2})[_\-]?(\d{2})", stem)
    if date_match:
        date_str = "_".join(date_match.groups())
    else:
        date_str = datetime.today().strftime("%Y_%m_%d")

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    base = out_dir / f"sales_{date_str}_matched"
    csv_path = base.with_suffix(".csv")
    xlsx_path = base.with_suffix(".xlsx")
    unmatch_path = out_dir / f"sales_{date_str}_unmatched.txt"

    # 미매칭 있을 때 txt 저장 (항상)
    if unmatched:
        with open(unmatch_path, "w", encoding="utf-8") as f:
            f.write(f"# 미매칭 항목 — {date_str}\n")
            for u in unmatched:
                f.write(u + "\n")
        print(f"\n📄 미매칭 목록 저장: {unmatch_path}")

    if unmatched and not force:
        print("❌ 미매칭 항목이 존재하여 CSV/XLSX를 생성하지 않습니다.")
        print("   --force 플래그를 사용하면 미매칭 포함 저장합니다.")
        return

    # 최종 컬럼만 선택
    out = df[FINAL_COLS].copy()

    # CSV 저장 (utf-8-sig — 엑셀 한글 호환)
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 CSV 저장: {csv_path}")

    # XLSX 저장
    out.to_excel(xlsx_path, index=False)
    print(f"💾 XLSX 저장: {xlsx_path}")

    return csv_path, xlsx_path


# ──────────────────────────────────────────────
# 핵심 실행 로직 (터미널 / Colab 공용)
# ──────────────────────────────────────────────

def run(
    sales: str,
    master: str,
    force: bool = False,
    fuzzy_threshold: float = 0.75,
):
    """
    터미널과 Google Colab 양쪽에서 호출 가능한 공용 진입점.

    Parameters
    ----------
    sales           : 판매현황 xlsx 경로
    master          : 분류기준표 csv/xlsx 경로
    force           : True이면 미매칭 포함 강제 저장
    fuzzy_threshold : difflib 퍼지 매칭 유사도 임계값 (기본 0.75)
    """
    # 파일 존재 확인
    if not Path(sales).exists():
        print(f"❌ 판매현황 파일을 찾을 수 없습니다: {sales}")
        return
    if not Path(master).exists():
        print(f"❌ 분류기준표 파일을 찾을 수 없습니다: {master}")
        return

    print(f"\n📂 판매현황   : {sales}")
    print(f"📂 분류기준표 : {master}")
    print(f"   퍼지 매칭 임계값: {fuzzy_threshold}")

    # 데이터 로드
    master_df, plu_col, name_col = load_master(master)
    sales_df = load_sales(sales)

    print(f"\n[구조 확인]")
    print(f"  분류기준표 컬럼: {list(master_df.columns[:8])}")
    print(f"  판매현황 컬럼 수: {len(sales_df.columns)}")
    print(f"  판매현황 샘플 (상위 3개):")
    print(sales_df[["상품명", "매출합계", "00H", "12H", "23H"]].head(3).to_string(index=False))

    # 매칭 실행
    print("\n🔄 매칭 중...")
    result_df, unmatched, fuzzy_matched = match_products(
        sales_df, master_df, plu_col, name_col
    )

    # 보고 및 저장 판단
    can_save = report(result_df, unmatched, fuzzy_matched)

    if can_save or force:
        return save_outputs(result_df, sales, unmatched, force)
    else:
        print("\n미매칭 항목을 해결한 뒤 다시 실행하거나, force=True 로 강제 저장하세요.")
        return None


# ──────────────────────────────────────────────
# 진입점 — 터미널 전용 (Colab에서는 run() 직접 호출)
# ──────────────────────────────────────────────

def _is_colab() -> bool:
    """Google Colab / IPython 커널 환경 감지"""
    try:
        shell = get_ipython().__class__.__name__  # type: ignore[name-defined]  # noqa
        return "ZMQ" in shell or "Colab" in shell or "Terminal" not in shell
    except NameError:
        return False


def main():
    # Colab/Jupyter 환경이면 argparse 대신 안내 메시지 출력
    if _is_colab():
        print("=" * 60)
        print("  Google Colab / Jupyter 환경이 감지되었습니다.")
        print("  argparse 대신 run() 함수를 직접 호출하세요.\n")
        print("  사용 예시:")
        print("    from converter import run")
        print("    run(")
        print('        sales="판매현황_2026_04_01.xlsx",')
        print('        master="분류기준표.csv",')
        print("    )")
        print("=" * 60)
        return

    parser = argparse.ArgumentParser(
        description="판매현황 xlsx → PLU 매칭 → ML-ready CSV 변환기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sales",  required=True, help="판매현황 xlsx 경로")
    parser.add_argument("--master", required=True, help="분류기준표 csv/xlsx 경로")
    parser.add_argument(
        "--force",
        action="store_true",
        help="미매칭 항목이 있어도 강제 저장 (PLU 빈칸으로 출력)",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.75,
        help="퍼지 매칭 유사도 임계값 (기본: 0.75)",
    )
    args = parser.parse_args()

    run(
        sales=args.sales,
        master=args.master,
        force=args.force,
        fuzzy_threshold=args.fuzzy_threshold,
    )


# Colab/Jupyter 환경에서는 main() 자동 실행 차단
# → run() 함수를 직접 호출하세요 (파일 상단 docstring 참고)
if __name__ == "__main__" and not _is_colab():
    main()
