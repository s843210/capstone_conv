-- V7: 학생 앱 상품 신청 내역

CREATE TABLE IF NOT EXISTS student_product_request (
    id         BIGSERIAL PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    sales_date DATE NOT NULL,
    plu_code   VARCHAR(50) NOT NULL,
    quantity   INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_student_product_request UNIQUE (student_id, sales_date, plu_code),
    CONSTRAINT chk_student_product_request_quantity_positive CHECK (quantity > 0),
    CONSTRAINT fk_student_product_request_product_plu
        FOREIGN KEY (plu_code) REFERENCES product(plu_code)
);

CREATE INDEX IF NOT EXISTS idx_student_product_request_date
    ON student_product_request (sales_date);

CREATE INDEX IF NOT EXISTS idx_student_product_request_student_date
    ON student_product_request (student_id, sales_date);
