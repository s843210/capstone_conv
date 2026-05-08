from __future__ import annotations

import re
from difflib import get_close_matches, SequenceMatcher
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
UNMATCHED_CSV = BASE_DIR / "outputs" / "reports" / "unmatched_after_merge.csv"
MASTER_CSV = BASE_DIR / "data" / "processed" / "product_master.csv"

OUT_TXT = BASE_DIR / "outputs" / "reports" / "unmatched_product_name_analysis.txt"
OUT_CANDIDATES_CSV = BASE_DIR / "outputs" / "reports" / "unmatched_product_name_candidates.csv"


def normalize_text(value: object) -> str:
    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def has_space_diff(s: str) -> bool:
    return bool(re.search(r"\s{2,}", s)) or (" " in s)


def has_parenthesis(s: str) -> bool:
    return bool(re.search(r"[\(\)\[\]{}]", s))


def has_special_char(s: str) -> bool:
    return bool(re.search(r"[^0-9A-Za-z가-힣\s]", s))


def has_capacity_token(s: str) -> bool:
    return bool(
        re.search(
            r"\d+\s?(ml|mL|ML|l|L|g|kg|KG|oz|개입|입|봉|팩|pet|PET|캔|병)",
            s,
        )
    )


def has_event_text(s: str) -> bool:
    keywords = ["증정", "행사", "+1", "1+1", "2+1", "덤", "사은품", "기획", "한정", "할인"]
    s_low = s.lower()
    return any(k.lower() in s_low for k in keywords)


def has_case_diff(s: str) -> bool:
    return any(ch.isalpha() for ch in s) and (s.lower() != s or s.upper() != s)


def has_digit(s: str) -> bool:
    return bool(re.search(r"\d", s))


def build_candidates(unmatched_name: str, master_names: list[str], n: int = 3) -> list[tuple[str, float]]:
    # 1) difflib close matches
    close = get_close_matches(unmatched_name, master_names, n=10, cutoff=0.45)

    scored: list[tuple[str, float]] = []
    for cand in close:
        score = SequenceMatcher(None, unmatched_name, cand).ratio()
        scored.append((cand, score))

    # 2) fallback token-based broad scan if close is too small
    if len(scored) < n:
        key = re.sub(r"[^0-9A-Za-z가-힣]", "", unmatched_name.lower())
        for cand in master_names:
            ckey = re.sub(r"[^0-9A-Za-z가-힣]", "", cand.lower())
            if key and (key[:3] in ckey or ckey[:3] in key):
                score = SequenceMatcher(None, unmatched_name, cand).ratio()
                scored.append((cand, score))

    # dedupe and sort
    uniq: dict[str, float] = {}
    for name, score in scored:
        if name not in uniq or score > uniq[name]:
            uniq[name] = score

    out = sorted(uniq.items(), key=lambda x: x[1], reverse=True)[:n]
    return out


def main() -> None:
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)

    if not UNMATCHED_CSV.exists():
        raise FileNotFoundError(f"Unmatched file not found: {UNMATCHED_CSV}")
    if not MASTER_CSV.exists():
        raise FileNotFoundError(f"Product master not found: {MASTER_CSV}")

    unmatched = pd.read_csv(UNMATCHED_CSV, low_memory=False)
    master = pd.read_csv(MASTER_CSV, low_memory=False)

    if "product_name_norm" not in unmatched.columns:
        raise KeyError("'product_name_norm' column not found in unmatched file.")
    if "row_count" not in unmatched.columns:
        raise KeyError("'row_count' column not found in unmatched file.")
    if "product_name" not in master.columns:
        raise KeyError("'product_name' column not found in product master.")

    unmatched["product_name_norm"] = unmatched["product_name_norm"].map(normalize_text)
    master_names = (
        master["product_name"].astype(str).map(normalize_text).dropna().drop_duplicates().tolist()
    )

    # 2) analyze top unmatched by frequency
    top_unmatched = unmatched.sort_values("row_count", ascending=False).copy()

    # 3) pattern checks
    top_unmatched["pattern_space_diff"] = top_unmatched["product_name_norm"].map(has_space_diff)
    top_unmatched["pattern_parenthesis"] = top_unmatched["product_name_norm"].map(has_parenthesis)
    top_unmatched["pattern_special_char"] = top_unmatched["product_name_norm"].map(has_special_char)
    top_unmatched["pattern_capacity"] = top_unmatched["product_name_norm"].map(has_capacity_token)
    top_unmatched["pattern_event_text"] = top_unmatched["product_name_norm"].map(has_event_text)
    top_unmatched["pattern_case_diff"] = top_unmatched["product_name_norm"].map(has_case_diff)
    top_unmatched["pattern_digit"] = top_unmatched["product_name_norm"].map(has_digit)

    # 4,5) candidate search
    cand_rows: list[dict[str, object]] = []
    for _, row in top_unmatched.iterrows():
        name = str(row["product_name_norm"])
        cnt = int(row["row_count"])
        cands = build_candidates(name, master_names, n=3)
        if not cands:
            cand_rows.append(
                {
                    "product_name_norm": name,
                    "row_count": cnt,
                    "candidate_1": "",
                    "score_1": None,
                    "candidate_2": "",
                    "score_2": None,
                    "candidate_3": "",
                    "score_3": None,
                }
            )
        else:
            padded = cands + [("", 0.0)] * (3 - len(cands))
            cand_rows.append(
                {
                    "product_name_norm": name,
                    "row_count": cnt,
                    "candidate_1": padded[0][0],
                    "score_1": round(float(padded[0][1]), 4),
                    "candidate_2": padded[1][0],
                    "score_2": round(float(padded[1][1]), 4),
                    "candidate_3": padded[2][0],
                    "score_3": round(float(padded[2][1]), 4),
                }
            )

    candidates_df = pd.DataFrame(cand_rows)
    candidates_df.to_csv(OUT_CANDIDATES_CSV, index=False, encoding="utf-8-sig")

    # summary report
    total_unmatched_names = len(top_unmatched)
    lines: list[str] = []
    lines.append("Unmatched Product Name Analysis")
    lines.append(f"input_unmatched_csv: {UNMATCHED_CSV.as_posix()}")
    lines.append(f"input_product_master_csv: {MASTER_CSV.as_posix()}")
    lines.append(f"output_candidates_csv: {OUT_CANDIDATES_CSV.as_posix()}")
    lines.append("")
    lines.append(f"total_unmatched_names_analyzed: {total_unmatched_names}")
    lines.append(f"total_unmatched_rows_sum: {int(top_unmatched['row_count'].sum())}")
    lines.append("")
    lines.append("[Pattern Counts]")
    lines.append(f"space_diff: {int(top_unmatched['pattern_space_diff'].sum())}")
    lines.append(f"parenthesis: {int(top_unmatched['pattern_parenthesis'].sum())}")
    lines.append(f"special_char: {int(top_unmatched['pattern_special_char'].sum())}")
    lines.append(f"capacity_token: {int(top_unmatched['pattern_capacity'].sum())}")
    lines.append(f"event_text: {int(top_unmatched['pattern_event_text'].sum())}")
    lines.append(f"case_diff: {int(top_unmatched['pattern_case_diff'].sum())}")
    lines.append(f"digit: {int(top_unmatched['pattern_digit'].sum())}")
    lines.append("")
    lines.append("[Top 30 Unmatched + Candidate 3]")

    preview = top_unmatched[["product_name_norm", "row_count"]].merge(
        candidates_df[
            [
                "product_name_norm",
                "candidate_1",
                "score_1",
                "candidate_2",
                "score_2",
                "candidate_3",
                "score_3",
            ]
        ],
        on="product_name_norm",
        how="left",
    ).head(30)
    lines.append(preview.to_string(index=False))

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved analysis report: {OUT_TXT}")
    print(f"Saved candidates csv: {OUT_CANDIDATES_CSV}")
    print(f"Analyzed unmatched names: {total_unmatched_names}")


if __name__ == "__main__":
    main()
