# AI 수요예측 파이프라인 (에러없조)

조선대학교 교내 emart24 AI 기반 수요예측 및 발주 추천 시스템

## 프로젝트 구조

```
Ai/
├── config/
│   └── config.yaml          # 경로·파라미터 설정
├── src/
│   ├── config.py             # 설정 로더
│   ├── utils/                # 공통 유틸리티
│   │   ├── io.py             # CSV/Excel 읽기·쓰기
│   │   ├── date_parse.py     # 날짜 파싱
│   │   ├── text_norm.py      # 텍스트 정규화
│   │   ├── encoding.py       # LabelEncoding
│   │   └── report.py         # 리포트 작성
│   ├── pipeline/             # 핵심 파이프라인
│   │   ├── ingest.py         # 원본 데이터 병합
│   │   ├── preprocess.py     # 전처리·데이터셋 구축
│   │   ├── features.py       # 피처 엔지니어링
│   │   ├── train.py          # 모델 학습
│   │   └── infer.py          # 예측·발주 추천
│   ├── serving/
│   │   └── preprocess_for_infer.py  # FastAPI 연동용 추론 모듈
│   └── legacy/               # 기존 번호형 스크립트 (참고용)
├── models/
│   └── random_forest_fast_model.pkl  # 학습 완료 모델
├── tests/
│   └── test_smoke.py         # 스모크 테스트
├── run_pipeline.py           # 통합 실행 엔트리포인트
└── requirements.txt
```

## 빠른 시작

### 1. 환경 설정
```bash
pip install -r requirements.txt
```

### 2. 스모크 테스트 (모델 로드 + 예측 검증)
```bash
python tests/test_smoke.py
```

### 3. 파이프라인 실행

```bash
# 전체 파이프라인 (원본 데이터 필요)
python run_pipeline.py --step all

# 개별 단계
python run_pipeline.py --step ingest       # 원본 데이터 병합
python run_pipeline.py --step preprocess   # 전처리
python run_pipeline.py --step features     # 피처 생성
python run_pipeline.py --step train        # 모델 학습
python run_pipeline.py --step predict      # 예측 + 발주 추천

# 대화형 테스트
python run_pipeline.py --step interactive
```

## 실행 순서 (재학습 시)

```
ingest → preprocess → features → train → predict
```

1. **ingest**: 판매 Excel 파일 + 상품 마스터 → CSV 병합
2. **preprocess**: 판매+상품 결합, 정제, 중복 제거 → final_sales_dataset.csv
3. **features**: 학사일정 + 시간표 + lag/rolling 피처 → model_features.csv
4. **train**: Baseline/RF/LightGBM 학습 → model.pkl
5. **predict**: 모델 로드 → 내일 예측 → 발주 추천 CSV

## 재학습에 필요한 원본 데이터

| 데이터 | 경로 |
|--------|------|
| POS 판매 엑셀 | `data/raw/sales/**/*.xlsx` |
| 상품 마스터 | `data/raw/product/product_master/csv_상품분류기준표/` |
| 학사일정 | `data/raw/calendar/academic_calendar_2026.csv` |
| 시간표 (2024-2025) | `data/raw/timetable/timetable_2024_2025.xlsx` |
| 시간표 (2026) | `data/raw/timetable/timetable_2026.xlsx` |

## FastAPI 연동

```python
from src.serving.preprocess_for_infer import ModelPredictor

predictor = ModelPredictor()  # or ModelPredictor("path/to/model.pkl")
result = predictor.predict_one({"plu_code": "8801056040925.0", ...})
# → {"predicted_sales_qty": 18.42, "recommended_order_qty": 23}
```

## 설정 변경

`config/config.yaml`에서 모든 경로와 파라미터 수정 가능:
- 데이터/모델 경로
- 학습 기간 (train_start, train_end, test_start)
- safety_factor, guardrail 파라미터
- 모델 하이퍼파라미터
