CREATE TABLE IF NOT EXISTS ai_run (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL UNIQUE,
    run_type VARCHAR(30) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL,
    target_date DATE,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds DOUBLE PRECISION,
    row_count INT,
    prediction_csv VARCHAR(500),
    recommendation_csv VARCHAR(500),
    request_payload TEXT,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_run_target_date ON ai_run(target_date);
CREATE INDEX IF NOT EXISTS idx_ai_run_started_at ON ai_run(started_at);
CREATE INDEX IF NOT EXISTS idx_ai_run_status ON ai_run(status);
