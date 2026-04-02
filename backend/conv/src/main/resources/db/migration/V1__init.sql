-- 1. 상품 마스터 테이블 (기준 정보)
CREATE TABLE product (
                         id            BIGSERIAL PRIMARY KEY,           -- 시스템 내부 고유 ID
                         plu_code      VARCHAR(50) NOT NULL UNIQUE,     -- 실제 상품 바코드 (가장 중요한 식별자)
                         name          VARCHAR(255) NOT NULL,           -- 상품명 (예: 참치마요 삼각김밥)
                         category      VARCHAR(100) DEFAULT '기타/미분류', -- 상품 카테고리 (대분류)
                         current_stock INT DEFAULT 0,                   -- 현재 매장 재고 수량
                         is_active     BOOLEAN DEFAULT TRUE,            -- 판매 중단 여부
                         updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 마지막 재고 업데이트 시점
);

-- 2. AI 발주 예측 결과 테이블 (트랜잭션 데이터)
CREATE TABLE ai_prediction (
                               id                BIGSERIAL PRIMARY KEY,       -- 예측 기록 고유 ID
                               product_id        BIGINT NOT NULL,             -- 어떤 상품에 대한 예측인지 (FK)
                               target_date       DATE NOT NULL,               -- '언제'에 대한 예측인가 (예: 2026-04-03)
                               predicted_sales   INT NOT NULL,                -- AI가 예측한 예상 판매량
                               recommended_order INT NOT NULL,                -- AI가 제안하는 권장 발주량
                               confidence_score  FLOAT,                       -- 예측 신뢰도 (0.0 ~ 1.0)
                               ai_insight        VARCHAR(255),                -- 사장님께 보여줄 한 줄 근거
                               created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- AI가 데이터를 던져준 시점

    -- 외래키 설정: 상품이 삭제되면 해당 예측 데이터도 관리되도록 설정
                               CONSTRAINT fk_product FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
);

-- 3. 빠른 조회를 위한 인덱스 (옵션)
CREATE INDEX idx_prediction_date ON ai_prediction(target_date);