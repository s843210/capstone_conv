CREATE TABLE IF NOT EXISTS student_suggestion (
    id BIGSERIAL PRIMARY KEY,
    writer VARCHAR(50) NOT NULL,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'UNREAD',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_student_suggestion_title_not_blank CHECK (BTRIM(title) <> ''),
    CONSTRAINT chk_student_suggestion_content_not_blank CHECK (BTRIM(content) <> ''),
    CONSTRAINT chk_student_suggestion_status CHECK (status IN ('UNREAD', 'REVIEWING', 'DONE'))
);

CREATE INDEX IF NOT EXISTS idx_student_suggestion_updated_at
    ON student_suggestion (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_student_suggestion_writer
    ON student_suggestion (writer);
