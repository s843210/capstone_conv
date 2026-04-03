-- V4: 음수/NULL 재고를 0으로 정규화하고 비음수 제약 추가
UPDATE product
SET current_stock = 0
WHERE current_stock IS NULL
   OR current_stock < 0;

ALTER TABLE product
    ALTER COLUMN current_stock SET DEFAULT 0;

ALTER TABLE product
    ALTER COLUMN current_stock SET NOT NULL;

ALTER TABLE product
    DROP CONSTRAINT IF EXISTS chk_product_current_stock_non_negative;

ALTER TABLE product
    ADD CONSTRAINT chk_product_current_stock_non_negative CHECK (current_stock >= 0);
