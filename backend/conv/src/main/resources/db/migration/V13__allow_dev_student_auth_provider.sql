ALTER TABLE app_user
    DROP CONSTRAINT IF EXISTS chk_app_user_provider;

ALTER TABLE app_user
    ADD CONSTRAINT chk_app_user_provider
        CHECK (provider IN ('LOCAL', 'GOOGLE', 'DEV'));

ALTER TABLE app_user
    DROP CONSTRAINT IF EXISTS chk_app_user_google_subject;

ALTER TABLE app_user
    ADD CONSTRAINT chk_app_user_external_subject
        CHECK (
            provider NOT IN ('GOOGLE', 'DEV')
            OR (provider_user_id IS NOT NULL AND BTRIM(provider_user_id) <> '')
        );
