CREATE TABLE IF NOT EXISTS product_master (
    id BIGSERIAL PRIMARY KEY,
    plu_code VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_product_master_category ON product_master(category);

CREATE TABLE IF NOT EXISTS inventory_snapshot (
    id BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    product_id BIGINT NOT NULL,
    plu_code VARCHAR(50) NOT NULL,
    current_stock INT NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_inventory_snapshot_product
        FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE,
    CONSTRAINT uq_inventory_snapshot_date_product
        UNIQUE (snapshot_date, product_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_snapshot_date ON inventory_snapshot(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_inventory_snapshot_plu_code ON inventory_snapshot(plu_code);
