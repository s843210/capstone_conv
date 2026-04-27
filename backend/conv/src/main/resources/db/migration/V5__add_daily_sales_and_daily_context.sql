-- V5: 일자별 판매 이력 + 외생 컨텍스트 테이블 추가

-- 1) 일자별 상품 판매량 (전날 확정 판매 적재용)
CREATE TABLE IF NOT EXISTS daily_sales (
    id         BIGSERIAL PRIMARY KEY,
    sales_date DATE NOT NULL,
    plu_code   VARCHAR(50) NOT NULL,
    sales_qty  INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_daily_sales_date_plu UNIQUE (sales_date, plu_code),
    CONSTRAINT chk_daily_sales_qty_non_negative CHECK (sales_qty >= 0)
);

CREATE INDEX IF NOT EXISTS idx_daily_sales_date ON daily_sales (sales_date);
CREATE INDEX IF NOT EXISTS idx_daily_sales_plu_date ON daily_sales (plu_code, sales_date DESC);

-- 2) 예측 대상일 컨텍스트 (날씨/휴일/학사/유동인구)
CREATE TABLE IF NOT EXISTS daily_context (
    target_date        DATE PRIMARY KEY,
    avg_temp_c         DOUBLE PRECISION,
    precipitation_mm   DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_rain            SMALLINT NOT NULL DEFAULT 0,
    is_holiday         SMALLINT NOT NULL DEFAULT 0,
    academic_event     INT NOT NULL DEFAULT 0,
    building_headcount INT NOT NULL DEFAULT 0,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_daily_context_precip_non_negative CHECK (precipitation_mm >= 0),
    CONSTRAINT chk_daily_context_is_rain CHECK (is_rain IN (0, 1)),
    CONSTRAINT chk_daily_context_is_holiday CHECK (is_holiday IN (0, 1)),
    CONSTRAINT chk_daily_context_headcount_non_negative CHECK (building_headcount >= 0)
);
