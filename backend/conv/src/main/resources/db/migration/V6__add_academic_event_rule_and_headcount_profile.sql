-- V6: 학사 이벤트 규칙 + 요일별 유동인구 프로필

CREATE TABLE IF NOT EXISTS academic_event_rule (
    id         BIGSERIAL PRIMARY KEY,
    event_code INT NOT NULL,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    event_name VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_academic_event_rule_code CHECK (event_code BETWEEN 0 AND 4),
    CONSTRAINT chk_academic_event_rule_range CHECK (start_date <= end_date)
);

CREATE INDEX IF NOT EXISTS idx_academic_event_rule_range
    ON academic_event_rule (start_date, end_date);

CREATE TABLE IF NOT EXISTS building_headcount_profile (
    id            SMALLINT PRIMARY KEY,
    monday        INT NOT NULL DEFAULT 20,
    tuesday       INT NOT NULL DEFAULT 20,
    wednesday     INT NOT NULL DEFAULT 20,
    thursday      INT NOT NULL DEFAULT 20,
    friday        INT NOT NULL DEFAULT 20,
    default_count INT NOT NULL DEFAULT 20,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_headcount_profile_id CHECK (id = 1),
    CONSTRAINT chk_headcount_profile_monday CHECK (monday >= 0),
    CONSTRAINT chk_headcount_profile_tuesday CHECK (tuesday >= 0),
    CONSTRAINT chk_headcount_profile_wednesday CHECK (wednesday >= 0),
    CONSTRAINT chk_headcount_profile_thursday CHECK (thursday >= 0),
    CONSTRAINT chk_headcount_profile_friday CHECK (friday >= 0),
    CONSTRAINT chk_headcount_profile_default CHECK (default_count >= 0)
);

INSERT INTO building_headcount_profile (id, monday, tuesday, wednesday, thursday, friday, default_count)
VALUES (1, 20, 20, 20, 20, 20, 20)
ON CONFLICT (id) DO NOTHING;
