CREATE TABLE IF NOT EXISTS app_user (
    id BIGSERIAL PRIMARY KEY,
    login_id VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(30) NOT NULL,
    provider_user_id VARCHAR(255),
    role VARCHAR(30) NOT NULL,
    password_hash VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_app_user_login_id_not_blank CHECK (BTRIM(login_id) <> ''),
    CONSTRAINT chk_app_user_email_not_blank CHECK (email IS NULL OR BTRIM(email) <> ''),
    CONSTRAINT chk_app_user_name_not_blank CHECK (BTRIM(name) <> ''),
    CONSTRAINT chk_app_user_provider CHECK (provider IN ('LOCAL', 'GOOGLE')),
    CONSTRAINT chk_app_user_role CHECK (role IN ('ADMIN', 'STUDENT')),
    CONSTRAINT chk_app_user_local_password CHECK (
        provider <> 'LOCAL'
        OR (password_hash IS NOT NULL AND BTRIM(password_hash) <> '')
    ),
    CONSTRAINT chk_app_user_google_subject CHECK (
        provider <> 'GOOGLE'
        OR (provider_user_id IS NOT NULL AND BTRIM(provider_user_id) <> '')
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_user_login_id
    ON app_user (login_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_user_email
    ON app_user (email)
    WHERE email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_user_provider_user_id
    ON app_user (provider, provider_user_id)
    WHERE provider_user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_app_user_role
    ON app_user (role);

CREATE INDEX IF NOT EXISTS idx_app_user_provider
    ON app_user (provider);
