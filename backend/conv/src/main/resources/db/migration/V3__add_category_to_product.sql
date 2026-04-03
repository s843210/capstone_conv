-- V3: product 카테고리 컬럼 추가
ALTER TABLE product
    ADD COLUMN IF NOT EXISTS category VARCHAR(100);

-- 기존 데이터 보정
UPDATE product
SET category = '기타/미분류'
WHERE category IS NULL
   OR BTRIM(category) = '';

ALTER TABLE product
    ALTER COLUMN category SET DEFAULT '기타/미분류';

ALTER TABLE product
    ALTER COLUMN category SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_product_category ON product(category);
