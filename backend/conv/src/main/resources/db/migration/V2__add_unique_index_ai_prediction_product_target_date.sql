-- V2: ai_prediction 중복 데이터 정리 후 (product_id, target_date) 유니크 보장

-- 기존 중복 데이터가 있으면 created_at 최신(동률이면 id 큰 값) 1건만 남기고 제거
WITH ranked AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY product_id, target_date
               ORDER BY created_at DESC NULLS LAST, id DESC
           ) AS rn
    FROM ai_prediction
)
DELETE FROM ai_prediction ap
USING ranked r
WHERE ap.id = r.id
  AND r.rn > 1;

-- 상품별/일자별 예측값 1건만 허용
CREATE UNIQUE INDEX uq_ai_prediction_product_target_date
    ON ai_prediction (product_id, target_date);
