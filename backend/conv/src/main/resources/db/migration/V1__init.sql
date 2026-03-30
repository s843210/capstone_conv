-- 1. 상품 정보 테이블 (현재의 상태 관리)
CREATE TABLE product (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    current_stock INT DEFAULT 0, -- 대시보드용 최신 재고 (매일 18시 업데이트되는 값)
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. 일별 판매 및 마감 통계 (과거 이력/AI 학습용)
CREATE TABLE daily_sales_stats (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    sale_date DATE NOT NULL,
    closing_stock_18h INT NOT NULL, -- AI 피처: 해당 날짜 18시 시점의 재고 기록
    daily_sale_qty INT DEFAULT 0,   -- 해당 날짜의 총 판매량
    is_promotion BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (product_id) REFERENCES product(id)
);

-- 3. 날씨 데이터 (AI 예측 피처)
CREATE TABLE weather_data (
    id BIGSERIAL PRIMARY KEY,
    target_date DATE NOT NULL UNIQUE,
    temp FLOAT,
    condition_code VARCHAR(20),
    rain_yn BOOLEAN
);

-- 4. AI 발주 추천 결과
CREATE TABLE order_recommendation (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    predicted_demand INT NOT NULL,     -- AI 예측 수요
    recommended_qty INT NOT NULL,      -- 최종 추천 발주량
    prediction_confidence FLOAT,       -- 예측 신뢰도
    weather_impact_rate INT DEFAULT 0, -- 날씨 영향 가중치 (%)
    ai_insight_reason VARCHAR(100),    -- 추천 사유 (예: "내일 비 소식으로 인한 우산 수요 증가")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES product(id)
);