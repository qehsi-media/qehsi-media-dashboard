-- qehsi-media-dashboard SQLite 表结构
-- 字段名一旦确定，后续代码严格复用

CREATE TABLE IF NOT EXISTS accounts (
    account_id    TEXT PRIMARY KEY,
    platform      TEXT NOT NULL,                                   -- douyin / wechat_video / wechat_mp
    account_name  TEXT NOT NULL,
    account_group TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    UNIQUE (platform, account_name)
);

CREATE TABLE IF NOT EXISTS contents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    platform      TEXT NOT NULL,
    account_name  TEXT NOT NULL,
    content_title TEXT NOT NULL,
    publish_time  TEXT,                                            -- YYYY-MM-DD HH:MM:SS
    views         INTEGER NOT NULL DEFAULT 0,                      -- 播放量 / 阅读量
    likes         INTEGER NOT NULL DEFAULT 0,
    comments      INTEGER NOT NULL DEFAULT 0,
    shares        INTEGER NOT NULL DEFAULT 0,
    favorites     INTEGER NOT NULL DEFAULT 0,
    link          TEXT,
    content_type  TEXT,
    topic         TEXT,
    upload_batch  INTEGER,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (upload_batch) REFERENCES upload_batches (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contents_platform ON contents (platform);
CREATE INDEX IF NOT EXISTS idx_contents_account ON contents (account_name);
CREATE INDEX IF NOT EXISTS idx_contents_publish_time ON contents (publish_time);
CREATE INDEX IF NOT EXISTS idx_contents_topic ON contents (topic);

CREATE TABLE IF NOT EXISTS field_mappings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    platform      TEXT NOT NULL,
    source_column TEXT NOT NULL,
    target_field  TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (platform, source_column)
);

CREATE TABLE IF NOT EXISTS upload_batches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    platform    TEXT NOT NULL,
    file_name   TEXT NOT NULL,
    upload_time TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    row_count   INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    report_month   TEXT NOT NULL,                                  -- YYYY-MM
    report_content TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS activities (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_name      TEXT NOT NULL,
    activity_date      TEXT,
    goal               TEXT,
    suggested_accounts TEXT,
    battle_plan        TEXT,
    status             TEXT NOT NULL DEFAULT '筹备中',
    created_at         TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
