ALTER TABLE daily_context
    ADD COLUMN IF NOT EXISTS is_start_semester SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_end_semester SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_exam SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_vacation SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_festival SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_holiday_or_no_class SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS class_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS monday_class_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tuesday_class_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS wednesday_class_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS thursday_class_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS friday_class_count INT NOT NULL DEFAULT 0;

ALTER TABLE daily_context
    ADD CONSTRAINT chk_daily_context_is_start_semester CHECK (is_start_semester IN (0, 1)),
    ADD CONSTRAINT chk_daily_context_is_end_semester CHECK (is_end_semester IN (0, 1)),
    ADD CONSTRAINT chk_daily_context_is_exam CHECK (is_exam IN (0, 1)),
    ADD CONSTRAINT chk_daily_context_is_vacation CHECK (is_vacation IN (0, 1)),
    ADD CONSTRAINT chk_daily_context_is_festival CHECK (is_festival IN (0, 1)),
    ADD CONSTRAINT chk_daily_context_is_holiday_or_no_class CHECK (is_holiday_or_no_class IN (0, 1)),
    ADD CONSTRAINT chk_daily_context_class_count_non_negative CHECK (class_count >= 0),
    ADD CONSTRAINT chk_daily_context_monday_class_count_non_negative CHECK (monday_class_count >= 0),
    ADD CONSTRAINT chk_daily_context_tuesday_class_count_non_negative CHECK (tuesday_class_count >= 0),
    ADD CONSTRAINT chk_daily_context_wednesday_class_count_non_negative CHECK (wednesday_class_count >= 0),
    ADD CONSTRAINT chk_daily_context_thursday_class_count_non_negative CHECK (thursday_class_count >= 0),
    ADD CONSTRAINT chk_daily_context_friday_class_count_non_negative CHECK (friday_class_count >= 0);
