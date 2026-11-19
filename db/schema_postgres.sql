CREATE TABLE IF NOT EXISTS accounts (
    account_id    TEXT PRIMARY KEY,
    platform      TEXT NOT NULL,
    account_name  TEXT NOT NULL,
    account_group TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    UNIQUE (platform, account_name)
);

CREATE TABLE IF NOT EXISTS upload_batches (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform    TEXT NOT NULL,
    file_name   TEXT NOT NULL,
    upload_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_count   INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS contents (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform      TEXT NOT NULL,
    account_name  TEXT NOT NULL,
    content_title TEXT NOT NULL,
    publish_time  TEXT,
    views         INTEGER NOT NULL DEFAULT 0,
    likes         INTEGER NOT NULL DEFAULT 0,
    comments      INTEGER NOT NULL DEFAULT 0,
    shares        INTEGER NOT NULL DEFAULT 0,
    favorites     INTEGER NOT NULL DEFAULT 0,
    link          TEXT,
    content_type  TEXT,
    topic         TEXT,
    upload_batch  INTEGER REFERENCES upload_batches (id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contents_platform ON contents (platform);
CREATE INDEX IF NOT EXISTS idx_contents_account ON contents (account_name);
CREATE INDEX IF NOT EXISTS idx_contents_publish_time ON contents (publish_time);
CREATE INDEX IF NOT EXISTS idx_contents_topic ON contents (topic);

CREATE TABLE IF NOT EXISTS field_mappings (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform      TEXT NOT NULL,
    source_column TEXT NOT NULL,
    target_field  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, source_column)
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_month   TEXT NOT NULL,
    report_content TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
