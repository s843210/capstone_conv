# 🚀 파이프라인 실행 명령어 사용법 (run_pipeline.py)

AI 수요예측 및 발주 추천 파이프라인을 터미널(CMD/PowerShell)에서 쉽게 실행할 수 있도록 통합된 명령어 모음입니다.

---

## 💻 기본 실행 명령어 (가장 많이 사용됨)

### 1. 전체 재학습 (Full Pipeline)
```bash
python run_pipeline.py --step all
```
* **언제 쓰나요?** 처음에 원본 데이터를 폴더(`data/raw/`)에 모두 넣고, 처음부터 끝까지 모델을 새로 만들고 싶을 때 사용합니다.
* **실행 순서:** 데이터 병합(`ingest`) → 전처리(`preprocess`) → 피처 생성(`features`) → 모델 학습(`train`) → 발주량 예측(`predict`)까지 한 번에 실행됩니다.

### 2. 내일 발주량 예측만 하기
```bash
python run_pipeline.py --step predict
```
* **언제 쓰나요?** 이미 학습된 모델(`random_forest_fast_model.pkl`)이 존재할 때, 데이터만 최신으로 업데이트하고 내일 발주 추천량 결과 파일만 새로 뽑고 싶을 때 사용합니다.

### 3. 모델만 다시 학습하기
```bash
python run_pipeline.py --step train
```
* **언제 쓰나요?** 데이터 전처리는 이미 다 끝났는데, 하이퍼파라미터(`config/config.yaml`) 설정을 바꾸거나 다른 AI 모델(LightGBM 등)로 성능 비교만 다시 해보고 싶을 때 사용합니다.

---

## 🛠 세부 단계별 명령어 (디버깅/테스트용)

중간에 데이터가 잘 만들어졌나 한 단계씩 끊어서 테스트하거나 실행할 때 사용합니다.

### 데이터 병합하기 (Raw → CSV)
```bash
python run_pipeline.py --step ingest
```
* 흩어져 있는 판매 엑셀 파일들과 상품 마스터 파일들을 읽어 하나의 큰 CSV 파일로 병합합니다.

### 전처리하기 (정제 및 결합)
```bash
python run_pipeline.py --step preprocess
```
* 판매량 0 미만의 비정상 데이터 제거, 결측치 처리, 상품명 기반 매칭 등을 수행합니다.

### 피처 만들기 (학습용 데이터로 변환)
```bash
python run_pipeline.py --step features
```
* 학사일정, 시간표, 요일, 그리고 최근 7일/14일/28일 이동평균선(rolling) 등 AI가 학습할 수 있도록 피처(Column)를 26개로 확장합니다.

---

## 🕹 대화형 테스트 (Interactive Mode)

```bash
python run_pipeline.py --step interactive
```
* 터미널 창에 상품명이나 PLU 코드를 직접 입력하면, **그 자리에서 바로 예측 판매량과 추천 발주량을 띄워주는** 콘솔 테스트 기능입니다.
* 모델이 특정 상품에 대해 어떤 예측을 내놓는지 빠르게 점검할 때 매우 유용합니다.
